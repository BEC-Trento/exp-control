import zerorpc
import json
import yaml

dds_client = zerorpc.Client()
dds_client.connect('tcp://localhost:5767')


class Kernel:
    def __init__(self):
        print('Starting kernel...')
        self.data = None
        
    def compile(self, data):
        shot = json.loads(data['shot'])
        
        with open('/home/fish3/exp_control/config.yaml') as f:
            self.config = yaml.safe_load(f)
        
        self._program_dds(shot)
        
        print('Compiled shot and programmed DDSs.')
        
        return 'Compiled shot.'
    
    def _program_dds(self, data):
        
        dds = []
        for action in data['program'].values():
            if action['action'] in ['DdsAction', 'FullDdsAction']:
                key = action['board']
                
                # this will only work for one DDS for now
                ddss = self.config['new_dds_programming_list']
                if len(ddss) == 1 and key in ddss:
                    dds.append(action)
        
        dds.sort(key=lambda item: float(item['time']))
        
        lut = [item['state2'] for item in dds]
        
        print(lut)
        dds_client.program(lut)
        return 'DDS programmed.'


server = zerorpc.Server(Kernel())
server.bind('tcp://*:6778')
server.run()
