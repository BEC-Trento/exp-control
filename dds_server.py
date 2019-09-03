import zerorpc
import logging
import sys
from collections import defaultdict
from itertools import cycle

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

from dds_programmer import DDS

class DDS41:
    def __init__(self):
        self.dds = DDS('DDS41')
        logger.info('Spawning server...')
        
    def hello(self):
        return 'hello'

    def program(self, lut):
        
        # This is ugly but it will do for now
#        print(lut)
#        lut2 = []
#        for item1, item2 in zip(lut[::2], lut[1::2]):
#            lut2.append({**item1, **item2})
#            lut2.append({**item1, **item2})
#        print(lut)
#        print(lut2)

        
        self.dds.write_table(lut)


s = zerorpc.Server(DDS41())
s.bind('tcp://*:5767')
s.run()
