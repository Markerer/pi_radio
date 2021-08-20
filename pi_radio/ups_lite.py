#!/usr/bin/env python
import struct
import smbus
import sys
import time
import RPi.GPIO as GPIO
import subprocess


def readVoltage(bus):
    "This function returns as float the voltage from the Raspi UPS Hat via the provided SMBus object"
    address = 0x36
    read = bus.read_word_data(address, 0X02)
    swapped = struct.unpack("<H", struct.pack(">H", read))[0]
    voltage = swapped * 1.25 /1000/16
    return voltage

def readCapacity(bus):
    "This function returns as a float the remaining capacity of the battery connected to the Raspi UPS Hat via the provided SMBus object"
    address = 0x36
    read = bus.read_word_data(address, 0X04)
    swapped = struct.unpack("<H", struct.pack(">H", read))[0]
    capacity = swapped/256
    return capacity

def QuickStart(bus):
    address = 0x36
    bus.write_word_data(address, 0x06,0x4000)

def PowerOnReset(bus):
    address = 0x36
    bus.write_word_data(address, 0xfe,0x0054)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(4,GPIO.IN)

bus = smbus.SMBus(1)

PowerOnReset(bus)
QuickStart(bus)

while True:
    # if charge is below the percent and power adapter is not plugged in (not charging)
    if readCapacity(bus) < 20 and (GPIO.input(4) == GPIO.LOW):
        subprocess.call(['shutdown', '-h', 'now'], shell=False)
        
    time.sleep(2.0)
