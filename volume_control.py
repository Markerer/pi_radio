from time import sleep
import RPi.GPIO as GPIO
from ky040.KY040 import KY040
import alsaaudio

print(alsaaudio.cards())
mixer = alsaaudio.Mixer('SoftMaster')
print(mixer.getvolume())

# Define your pins
CLOCKPIN = 5
DATAPIN = 6
SWITCHPIN = 13

last_volume = 100

# Callback for rotary change
def rotaryChange(direction):
    current_volume = mixer.getvolume()[0]
    if(direction == 0 and current_volume >= 5):
        mixer.setvolume(current_volume - 5)
    if(direction == 1 and current_volume <= 95):
        mixer.setvolume(current_volume + 5)
    print('Current_volume: ', current_volume)
    print('New value: ', mixer.getvolume())

# Callback for switch button pressed
def switchPressed():
    global last_volume
    current_volume = mixer.getvolume()[0]
    if(current_volume > 0):
        mixer.setvolume(0)
        last_volume = current_volume
        print('Muted')
    else:
        mixer.setvolume(last_volume)
        print('Unmuted')

# Create a KY040 and start it
ky040 = KY040(CLOCKPIN, DATAPIN, SWITCHPIN, rotaryChange, switchPressed, rotaryBouncetime=25, switchBouncetime=750)
ky040.start()

# Keep your proccess running
try:
    while True:
        sleep(0.1)
finally:
    ky040.stop()
    GPIO.cleanup()
