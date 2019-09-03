#!/usr/bin/python3
#

"""
author: Arturo Farolfi

"""
import numpy as np
import serial
import serial.tools.list_ports
import argparse


parser = argparse.ArgumentParser(description='Set Marconi')
parser.add_argument('-f', '--freq', type=float,help='uw freq MHz')
parser.add_argument('-a', '--amp', type=float, help='uw amp dBm')                   
args = parser.parse_args()

ports = serial.tools.list_ports.comports()
# for p in ports:
#     print(ports)
names = [p.device for p in ports]
#print("Found ports:\n"+"\n".join(names))

product = 'USB-Serial Controller D'
ix = [p.product for p in ports].index(product)

port = ports[ix].device
print('Marconi found on port %s'%port)

Freq = args.freq

ser = serial.Serial(port,
                    9600,
                    stopbits=1,
                    parity=serial.PARITY_NONE,
                    timeout=2)
#go_remote = '\x01'
#ser.write(bytes(go_remote, encoding='ascii'))

ser.write(bytes("*IDN?;\n", encoding="ascii"))
a = ser.readline()
print("Found:\n"+str(a))

command_dict = {'freq': "CFRQ:VALUE {:.6f}MHZ;",
                'amp':  "RFLV:VALUE {:.2f}DBM;",
                }

for attr, cmd in command_dict.items():
    value = getattr(args, attr)
    if value is not None:

        command = cmd.format(value)
        ser.write(bytes(command, encoding="ascii"))
        print("Sent command: "+command)

ser.close()


