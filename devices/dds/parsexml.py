# -*- coding: utf-8 -*-
"""
author: CM

"""
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

filename = 'DDS27_freq_scan.xml'

tree = ET.ElementTree(file=filename)
root = tree.getroot()
print(root)
for child in root:
    print child.tag, child.text
    for ch0 in child.findall('ch0/fr'):
        print ch0.text
    

    
    
    
