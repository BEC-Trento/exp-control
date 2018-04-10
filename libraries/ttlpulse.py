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
#pylint: disable-msg=E0611

import program as lib_program

class Pulse(object):
    def __init__(self, system, name, comment=""):
    # the class needs to be added in the recognized list of actions (like the ramps)
    # syslist.py, line 141
    # and the get_prg needs to be handled by the Porgram library as well
    # program.py, line 68
        self.name = str(name)
        self.comment = str(comment)

        self.system = system

    def get_prg(self):
        return lib_program.Program(self.system, "")

class TTLPulse(Pulse):
    def __init__(self, system, act_on_name="", act_off_name="",
                 pulse_t=None, polarity=None,
                 name="", comment=""):

        super(TTLPulse, self).__init__(system, name, comment)
        
        if pulse_t is not None:
            pulse_t = float(pulse_t)
        self.pulse_t = pulse_t
        if polarity is not None:
            self.polarity = bool(polarity)
        else:
            self.polarity = True
        

        self.act_on_name = str(act_on_name)
        self.act_off_name = str(act_off_name)
        

    def get_prg(self):

        program = lib_program.Program(system=self.system, name=self.name, comment=self.comment)

        if None not in [self.polarity, self.pulse_t]:
            if self.polarity:
                act_1 = self.act_on_name
                act_2 = self.act_off_name
            else:
                act_1 = self.act_off_name
                act_2 = self.act_on_name
            program.add(self.system.set_time(0), act_1,)
            program.add(self.system.set_time(self.pulse_t), act_2,)
        else:
            print "ERROR: wrong call for \"%s\" with name \"%s\""%(str(type(self)), self.name)

        return program
