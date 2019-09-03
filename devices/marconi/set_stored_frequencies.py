#!/usr/bin/python3
#

"""
author: Arturo Farolfi

"""
import numpy as np
import serial
import serial.tools.list_ports
import argparse

parser = argparse.ArgumentParser(description='Set stored frequencies of the Marconi')
parser.add_argument('-f', '--freq', type=float,help='uw freq MHz')
parser.add_argument('-a', '--amp', type=float, help='uw amp dBm')                   
args = parser.parse_args()

