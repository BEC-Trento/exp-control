#!/usr/bin/python2
# -*- coding: utf-8 -*-

# Copyright (C) 2015-2016  Simone Donadello
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#pylint: disable-msg=E1101

import pylibftdi, threading
#from collections import OrderedDict

import libraries.parser as lib_parser
import libraries.syscommands as lib_syscommand
import libraries.command as lib_command
import libraries.syslist as lib_syslist
import libraries.instruction as lib_instruction
import libraries.fpga as lib_fpga
import libraries.action as lib_action
import libraries.program as lib_program
import libraries.ramp as lib_ramp
import libraries.evaporation_ramp as lib_evap
from libraries import init_boards, init_actions, init_programs
import os, sys
import zerorpc
from collections import defaultdict
import yaml
from pathlib2 import Path

import json

last_program_path = '/mnt/sis-fish/last_program.json'

#change path
#os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

class System(object):
    _time_base = 10e6
    _time_multiplier = 1e-3
    time_formats = dict(time="%.4f", time_rel="%+.4f")

    def __init__(self, external_trigger=False):
        print "Experiment Control"
        print "https://github.com/BEC-Trento/exp-control"
        print "author: Simone Donadello - license: GNU GPLv3"
        print

        self.main_program = None
        self.external_trigger = bool(external_trigger)

        self.fpga_list = []
        self.board_list = []
        self.action_list = []

        self.init_fpgas()
        self.init_boards()
        self.init_actions()

        #TODO: it is not clear how these variables are used
        self.variables = dict()
        self.cmd_thread = lib_syscommand.SysCommand(self)
        self.parser = lib_parser.Parser(self)
        self.evap_ramp_gen = lib_evap.EvaporationRampGen(self)
        self.evap_ramp_name = ''

    @property
    def all_fpga_ready(self):
        status = self.get_fpga_status()
        tot_state = True
        for state in status:
            tot_state = tot_state and not state.running
        return tot_state

    def init_boards(self):
        #first load boards
        self.board_list = lib_syslist.BoardList(system=self)
        init_boards.board_list_init(self.board_list)

    def init_actions(self):
        #then load actions and programs
        self.action_list = lib_syslist.ActionList(system=self)
        init_actions.action_list_init(self.action_list)
        init_programs.program_list_init(self.action_list)

    def init_fpgas(self):
        new_list = pylibftdi.Driver().list_devices()
        self.fpga_list = []
        for n_id, name in enumerate(new_list):
            if name[1] == "DLP-FPGA":
                self.fpga_list.append(lib_fpga.Fpga(device_index=n_id))
        print "found %d FPGAs connected"%len(self.fpga_list)

    def get_fpga_status(self):
        status = []
        for fpga_id in self.fpga_list:
            status.append(fpga_id.get_status())
        return status

    def set_program(self, prg_name=None):
        if prg_name is None and self.main_program is not None:
            prg_name = self.main_program.name
        self.main_program = self.action_list.get(prg_name)
        if self.main_program is not None:
            print "loaded program '%s'"%self.main_program.name
        else:
            print "WARNING: loaded None program"

    def stop_sys_commands(self):
        self.cmd_thread.stop()

    def run_sys_commands(self):
        if self.main_program is not None:
            thread = threading.Thread(target=self.cmd_thread.start)
            thread.daemon = True
            self.cmd_thread.set_thread(thread)
            thread.start()
        else:
            print "ERROR: any program loaded in the system"

    def sys_commands_running(self):
        return self.cmd_thread.running

    def get_time(self, time):
        return float(time)/self._time_base/self._time_multiplier

    def set_time(self, time):
        return int(self._time_base*self._time_multiplier*float(time))

    def get_program_time(self, prg_name=None, *args, **kwargs):
        #TODO: control if the correct main program is loaded when it is called
        if prg_name is None:
            program = self.main_program
        else:
            program = self.action_list.get(prg_name, *args, **kwargs)
            if isinstance(program, lib_ramp.Ramp):
                program = program.get_prg()
        if isinstance(program, lib_program.Program):
            instrs_prg = program.get_all_instructions()
            if len(instrs_prg) > 0:
                return instrs_prg[-1].time
            else:
                return 0
        else:
            print "WARNING: any program loaded"
            return 0

    def check_instructions(self, instructions=None):
        #TODO: control if the correct main program is loaded when it is called
        problems = []
        problems_ix = []
        if instructions is None:
            instructions = self.main_program.get_all_instructions()
        valid = True
        first_density_error = False
        if len(instructions) >= 2:
            if len(instructions) >= 2**14:
                valid = False
                problems += instructions[2**14:]
                print "ERROR: too many instructions in the program, %d (maximum is 16k)"%len(instructions)

            fifo_size = 2*(2**11)
            prev_instr = instructions[0]
            prev_dds_instr = None
            for n_instr, instr in enumerate(instructions):
                if n_instr > 0:
                    time_delta = self._get_instr_time_diff(prev_instr, instr)
                    if time_delta < 4:
                        problems.append(instr)
                        problems_ix.append(n_instr)
                        valid = False
                        print "ERROR: too short time between actions '%s' and '%s' at time %f (minimum is 4 clock cicles)"%(prev_instr.action.name, instr.action.name, self.get_time(instr.time))
                    if time_delta > 2**32:
                        valid = False
                        problems.append(instr)
                        problems_ix.append(n_instr)
                        print "ERROR: too long time between actions '%s' and '%s' at time %f (maximum is ~429s)"%(prev_instr.action.name, instr.action.name, self.get_time(instr.time))
                    prev_instr = instr

                if len(instructions) >= fifo_size \
                        and n_instr in range(len(instructions) - fifo_size) \
                        and not first_density_error:
                    time_delta = self._get_instr_time_diff(instructions[n_instr],
                                                           instructions[fifo_size+n_instr])
                    if time_delta < fifo_size*20:
                        valid = False
                        problems += instructions[n_instr:fifo_size+n_instr]
                        first_density_error = True
                        print "ERROR: too dense operations starting at time %f (a rate of ~20 clock cicles per action can be sustained when the FIFO is empty)"%self.get_time(instructions[n_instr].time)

                if isinstance(instr.action, lib_action.DdsAction) \
                                        and prev_dds_instr is not None:
                    if instr.time - prev_dds_instr.time < 0.035 \
                            and instr.action.board == prev_dds_instr.action.board:
                        valid = False
                        problems.append(instr)
                        problems_ix.append(n_instr)
                        print "ERROR: DDS actions '%s' and '%s' at time %f are too close (a DDS action takes ~35us to complete)"%(prev_dds_instr.action.name, instr.action.name, self.get_time(instr.time))
                    prev_dds_instr = None
                if isinstance(instr.action, lib_action.DdsAction):
                    prev_dds_instr = instr

        return valid, problems, problems_ix

    def send_program_and_run(self):
        
        # Use a config file to set parameters
        with open('/home/fish3/exp_control/config.yaml') as f:
            self.config = yaml.safe_load(f)

        #TODO: control if the correct main program is loaded when it is called
        result = False
        if isinstance(self.main_program, lib_program.Program):
        # valid0 : error state
        # program_commands : actions for FPGA (time + binary)
        # instr_prg : instructions for FPGA (list of Action objects + time)
        # script_actions : list of ScriptAction objects
        
            valid0, program_commands, instr_prg, script_actions = self._get_program_commands()

            if not valid0:
                print 'ERRORS in program. Not executing.'
                os.system('beep -r 2') #this requires Linux' beep installed
                #TODO: try a more cross-platform solution
            else:
                while not self.all_fpga_ready:
                    print "FPGAs are still in execution. Waiting..."
                    sleep_event = threading.Event()
                    sleep_event.wait(1000*self._time_multiplier)

                print "running the current program"
                
                
                
                            
                if 'direct_run' not in self.main_program.name:
                    self._print_instructions(instr_prg)
                    print('SYSTEM SEQUENCE INDEX = {}'.format(self.sequence_index))
                    
                    instructions_dict = self._print_instructions(instr_prg)
                    data = {u'system': u'exp_control', 
                            u'shot': json.dumps(instructions_dict, sort_keys=True, indent=2)}
                    
                    with open(str(last_program_path + '.tmp'), 'w') as f:
                        f.write(data['shot'])
                    os.rename(last_program_path + '.tmp', last_program_path)

                    
                    if self.sys_commands_running():
                        print('Running in cmd thread.')
                        client = zerorpc.Client()
                        client.connect('tcp://192.168.1.151:6778')
#                        self.client.hello()
                        print(client.compile(data))
                        client.close()
                    else:
                        print('Running in main.')
#                        self.client.hello()
                        print(self.client.compile(data))

                for action in script_actions:
                    call = action.call()
                    print(call)
                    #TODO: how to manage exceptions or crashes here?
                    os.system(call)
                
                for fpga_id in self.fpga_list:
                    valid = fpga_id.send_program_and_run(program_commands)
                    result = result or valid
        else:
            print "WARNING: any program loaded"
        return result

    def _print_instructions(self, instructions):
        D = {}
        D[u'program'] = {}
        D[u'sequence_index'] = self.sequence_index
        for j, inst in enumerate(instructions):
            inst_d = inst._repr_dict()
            time = '{:.4f}'.format(self.get_time(inst_d['time']))
            D[u'program'][time] = inst_d
        D[u'program_name'] = self.main_program.name
        D[u'ramp_name'] = self.evap_ramp_name
        D[u'variables'] = self.variables
        return D
    
    def _jit_update(self, name, instructions):
        # just-in-time update of a selected value
        for instr in instructions:
            if isinstance(instr.action, lib_action.AnalogAction):
                if instr.action.name == name:
                    value = self.client.lock('banana')
                    instr.action.value += value
#                    print(instr.action.__dict__)

    def _ensure_ttl_off(self, instructions):
        """checks that at the end of the program the specified TTL channels are
        set to False.
        This prevents to leave running what is should not be left running"""
        
        ttls = defaultdict(lambda : defaultdict(list))
        boards = self.config['ensure_off'].keys()
        
        # search for all the instructions that change the value of the specified
        # channels.
        for instr in instructions:
            if isinstance(instr.action, lib_action.DigitalAction):
                if instr.action.board.name in boards:
                    for channel in self.config['ensure_off'][instr.action.board.name]:
                        if channel in instr.action.channel:
                            ch_idx = instr.action.channel.index(channel)
                            ttls[instr.action.board.name][channel].append(instr.action.status[ch_idx])
        
        # here ttls[board][channel] is a list of all states for that
        # channel of the board. They are time-ordered, so the last one will be 
        # the status of that TTL at the end of the program
        for board in ttls.keys():
            for channel in ttls[board].keys():
                last_status = ttls[board][channel][-1]
                if last_status is True:
                    raise Exception('Forgot to turn OFF {} {}.'.format(board, channel))

    
            
    def _program_dds(self, instructions):
    
        # terrible hack to get the DDSs working without LUT backsearches
        dds = defaultdict(list)
        
        # get DDS instructions and
        # group the actions that correspond to individual channels
        for instr in instructions:
            if isinstance(instr.action, lib_action.DdsAction):
#                    key = instr.action.board.name + '_' + str(instr.action.channel)
                key = instr.action.board.name
                if key in self.config['new_dds_programming_list']:
                    dds[key].append(instr)
        
        # make sure they are sorted and the time is not str
        # .time is actually int but I feel safer this way
        for k, v in dds.items():
            dds[k] = sorted(v, key=lambda item: float(item.time))
        
#        for k, v in dds.items():
#            for instr in v:
#                try:
#                    print(instr.action.kwargs)
#                except:
#                    pass
        
        # Get frequency and amplitude values and store them in the state key
        # increment n_lut starting from 1.
        # Now I can program the DDSs with a LUT generated from state and 
        # then each instruction will just increment the LUT
        for k, v in dds.items():
            for instr in v:

#            KILL MEEEEE
#                if instr.action.channel == 1:  
#                    instr.action.state = (instr.action.frequency, 
#                                          instr.action.amplitude,
#                                          None, None)
#                elif instr.action.channel == 2:
#                    instr.action.state = (None, None,
#                                          instr.action.frequency, 
#                                          instr.action.amplitude)
#                elif instr.action.channel == None:
#                    pass
                    # it's already a LUT action
#                        instr.action.state = (None, None,
#                                              instr.action.frequency, 
#                                              instr.action.amplitude)
#                else:
#                    raise Exception('Wrong DDS channel.')
#                
                try:
                    channel = 'ch{}'.format(instr.action.channel - 1)
                    instr.action.state2 = {channel: {}}
                    if instr.action.frequency:
                        instr.action.state2[channel]['frequency'] = instr.action.frequency
                    if instr.action.amplitude:
                        instr.action.state2[channel]['amplitude'] = instr.action.amplitude
                except TypeError:
                    # then this is a FullDdsAction
                    # take the values from the attributes, otherwise the functions
                    # will not work
                    
                    instr.action.state2 = {'ch0': {}, 'ch1': {}}
                    instr.action.state2['ch0']['frequency'] = instr.action.ch0_freq
                    instr.action.state2['ch0']['amplitude'] = instr.action.ch0_amp
                    instr.action.state2['ch0']['phase'] = instr.action.ch0_phase
                    instr.action.state2['ch1']['frequency'] = instr.action.ch1_freq
                    instr.action.state2['ch1']['amplitude'] = instr.action.ch1_amp
                    instr.action.state2['ch1']['phase'] = instr.action.ch1_phase
                    
                        
        
            
            lut = [instr.action.state2 for instr in v]
            print lut
            # this is ok but randomises the lut since set is not ordered
            # it will still work properly but I prefer seeing it ordered 
            # for now while I'm still debuging
            if not self.config.get('ordered_lut', True):
                lut_unique = list(set(lut))
            else:
                lut_unique = []
                for item in lut:
                    if item not in lut_unique:
                        lut_unique.append(item)
            
            # get LUT indices
            indices = [lut_unique.index(item) for item in lut]

            for idx, instr in zip(indices, v):
                instr.action.nn_lut = idx
                
                # Change this to True for new style DDS programming  
                if self.config.get('new_dds_programming_list', True):
                    instr.action.frequency = None
                    instr.action.amplitude = None
#                    if instr.action.channel is not None:
                    instr.action.n_lut = idx

        
        if self.config['debug']:
            for name, instrs in dds.items():
                print(name)
                for instr in instrs:
                    print(instr.time)
                    print(instr.action.__dict__)
                    print
                print 
        
        
    def _run_program(self):
        instrs_fpga = []
        if isinstance(self.main_program, lib_program.Program):
            instrs_prg = self.main_program.get_all_instructions()
            
            # Program the DDS new style
            if self.config.get('new_dds_programming_list', False):
                self._program_dds(instrs_prg)

            
            if self.config.get('lock_channel', False):
                for name in self.config['lock_channel']:
                    # contact feedforward server before executing the shot
                    self._jit_update(name, instrs_prg)
            
            if self.config.get('ensure_off', False):
                self._ensure_ttl_off(instrs_prg)

            
            # separate normal actions from ScriptActions here
            script_actions = []
            for j, instr in enumerate(instrs_prg):
                if isinstance(instr.action, lib_action.ScriptAction):
                    instrs_prg.pop(j)
                    script_actions.append(instr.action)

            valid, problems, problems_ix = self.check_instructions(instrs_prg)
            print
            if not valid:
                for ix, probl in zip(problems_ix, problems):
                    probl.parents[-1].get(probl.uuid).enable = False
                    instrs_prg[ix].enable = False

            prev_instr = lib_instruction.Instruction(0, lib_action.Action(self, "temp"))
            for curr_instr in instrs_prg:
                if curr_instr not in problems:
                    time_delta = self._get_instr_time_diff(prev_instr, curr_instr)
                    new_instr = lib_instruction.FpgaInstruction(time_delta, curr_instr)
                    instrs_fpga.append(new_instr)

                    prev_instr = curr_instr
                else:
                    print "WARNING: action '%s' at time %f wont be executed"%(curr_instr.action.name, self.get_time(curr_instr.time))

            end_instr = lib_instruction.FpgaInstruction(0, action=lib_action.EndAction(self))
            instrs_fpga.append(end_instr)

        return valid, instrs_fpga, instrs_prg, script_actions

    def _get_program_commands(self):
        cmd_list = []
        if isinstance(self.main_program, lib_program.Program):
            valid, instructions_fpga, instr_prg, script_actions = self._run_program()

            if self.external_trigger:
                cmd_list.append(lib_command.ExtTriggerOnCommand())
            else:
                cmd_list.append(lib_command.ExtTriggerOffCommand())

            for instr_num, instr in enumerate(instructions_fpga):
                cmd_list.append(lib_command.LoadCommand(memory=instr_num,
                                                        command=instr.action.command_bits,
                                                        time=instr.time,
                                                        address=instr.action.board.address,
                                                        data=instr.data))

            cmd_list.append(lib_command.LoadDoneCommand())

        return valid, cmd_list, instr_prg, script_actions

    def _get_instr_time_diff(self, prev_instr, curr_instr):
        if isinstance(prev_instr, lib_instruction.Instruction) and \
                    isinstance(curr_instr, lib_instruction.Instruction):
            delta_t = int(curr_instr.time - prev_instr.time)
            return max(0, delta_t)
        else:
            print "WARNING: wrong call to time interval function, two '%s' must be given"%(str(lib_instruction.Instruction))
            return None

    def _print_fpga_commands(self):
        for cmd in self._get_program_commands():
            print cmd.get_hex()
