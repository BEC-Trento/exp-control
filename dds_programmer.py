import subprocess
import logging
import sys
import re
from lxml import etree


logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

writetable = '/home/fish3/exp_control/copyramp/writetable_remote.sh'

class DDS:
    def __init__(self, name):
        self.name = name
        self._clock_frequency = 400e6
        self._lut = None
        self._filename = '/home/fish3/exp_control/banana.xml'
        self._remotefilename = '/home/pi/banana.xml'

        
    @property
    def clock_frequency(self):
        response = subprocess.run(f'{writetable} -g', capture_output=True, shell=True)
        print(response)
        value = re.findall('[+-]?\d+\.\d+', str(response.stderr))
        self._clock_frequency = float(value[0])
        
        logger.info(f'Get DDS frequency: {self._clock_frequency}')
        
        return self._clock_frequency
        
    @clock_frequency.setter
    def clock_frequency(self, value):
        subprocess.run(f'{writetable} -s {value}', shell=True)
        self._clock_frequency = value
        
        logger.info(f'Set DDS frequency: {self._clock_frequency}')
    
    def _write_lut_to_xml(self, lut):
        # first I want to say screw xml files since it's not the 90s anymore
        # let's say lut is an ordered list of dicts of dicts
                     
        root = etree.Element('ad9958s')
        for idx, item in enumerate(lut):
            elem = etree.SubElement(root, 'elem')
            elem.text = str(idx)
            
            for channel in ['ch0', 'ch1']:
                if item.get(channel, None):
                    ch = etree.SubElement(elem, channel)
                    
                    _ch = item[channel]
                    if _ch.get('frequency', None):
                        etree.SubElement(ch, 'fr').text = str(_ch['frequency'])
                    
                    if _ch.get('amplitude', None):
                        etree.SubElement(ch, 'am').text = str(_ch['amplitude'])
                        
                    if _ch.get('phase', None):
                        etree.SubElement(ch, 'ph').text = str(_ch['phase'])
                
        tree = etree.ElementTree(root)
        tree.write(self._filename, pretty_print=True, xml_declaration=True) 
    
    def _read_lut_from_xml(self, filename):
        # will write this later. For now I'll just do in-software verification
        return
                
    def write_table(self, lut, force=False, verify=False):
        
        if verify:
            self._lut = self.verify_table()
        
        if lut == self._lut and not force:
            logger.info('Cached table already loaded.')
            return
        
        self._write_lut_to_xml(lut)
        logger.info(f'Writing table to {self.name}.')
        subprocess.run(['scp', self._filename, f'pi@192.168.1.155:{self._remotefilename}'])
        subprocess.run(f'{writetable} -w {self._remotefilename}', shell=True)
        
        self._lut = lut
        
    def verify_table(self):
        filename = f'{self._remotefilename}_dds'
        
        logger.info(f'Reading table from {self.name}.')
        subprocess.run(f'{writetable} -r {filename}')
        
        return self._read_lut_from_xml(filename)
        


if __name__ == '__main__':
    
    dds = DDS('DDS41')
    
    print(dds.clock_frequency)
    dds.clock_frequency = 400e6
    
    lut = [{'ch0': {'frequency': 100e6, 'amplitude': 200}, 
            'ch1': {'frequency': 10e6, 'phase': 20}},
           {'ch0': {'frequency': 104e6, 'amplitude': 800}, 
            'ch1': {'frequency': 154e6}}]
    
    dds.write_table(lut)
#    dds.verify_table()
    
