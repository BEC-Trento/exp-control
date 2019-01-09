# -*- coding: utf-8 -*-
"""
author: Arturo Farolfi

"""
import numpy as np
import serial
from serial.tools import list_ports


ports = list_ports.comports()
# print("Found ports:\n"+"\n".join(names))
for p in ports:
    print('-----------')
    print(p.device)
    print(p.product)

product = 'USB-Serial Controller D'
ix = [p.product for p in ports].index(product)

dev = ports[ix].device
print(dev)



