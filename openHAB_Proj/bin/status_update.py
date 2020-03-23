#!/usr/bin/env python

# The input to the script will be the UID of the device
# Need to take this UID and update the devic 
import argparse
import sys
sys.path.append(r'/home/openhabian/Environments/env_1/openHAB_Proj/')
from openHAB_Proj.AeotechZW096 import AeotechZW096
parser = argparse.ArgumentParser()
parser.add_argument("-u","--UID",nargs="+", help="The UID of the device")
args = parser.parse_args()

for device in args.UID:
    a = AeotechZW096()
    a.UID = device
    a.read_status()
    a.update_devices_data()
