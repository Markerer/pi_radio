import radio_start
import time
import subprocess
import threading
import collections
import RPi.GPIO as GPIO
from ky040.KY040 import KY040
from lirc import RawConnection

threads = []
process = None

def start_radio():
    global process
    process = subprocess.Popen(['python', '-B', '/home/pi/lcd/radio_start.py'])
    set_diode('green')

def is_radio_running():
    global process
    if process is None:
        return False
    else:
        poll = process.poll()
        if poll is None:
            return True
        return False

def is_input_handling_running():
    global threads
    is_input_running = False
    counter = 0
    for t in threads:
        if (t.getName() == 'ir_thread' or t.getName() == 'rotary_thread'):
            counter += 1
    if counter == 2:
        is_input_running = True
    return is_input_running

def handle_rotary_encoder():
    CLOCKPIN = 7
    DATAPIN = 8
    SWITCHPIN = 3
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(CLOCKPIN, GPIO.IN)
    GPIO.setup(DATAPIN, GPIO.IN)
    GPIO.setup(SWITCHPIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(SWITCHPIN, GPIO.FALLING, bouncetime=750)
    try:
        while True:
            if is_radio_running():
                return
            time.sleep(0.2)
            if GPIO.event_detected(SWITCHPIN):
                if GPIO.input(SWITCHPIN) == 0:
                    print('starting radio from rotary')
                    start_radio()
    finally:
        GPIO.setmode(GPIO.BCM)
        GPIO.remove_event_detect(DATAPIN)
        GPIO.remove_event_detect(SWITCHPIN)
        time.sleep(5)

def handle_ir_remote():
    ir_conn = RawConnection()
    #get IR command
    #keypress format = (hexcode, repeat_num, command_key, remote_id)
    while True:
        if is_radio_running():
            return
        try:
            keypress = ir_conn.readline(.0001)
        except:
            keypress=""

        time.sleep(0.1)
        
        if (keypress != "" and keypress != None):
                    
            data = keypress.split()
            sequence = data[1]
            command = data[2]
            
            #ignore command repeats
            if (sequence != "00"):
                continue
            
            if(command == 'KEY_POWER'):
                print('starting radio from ir')
                ir_conn.close()
                start_radio()
            elif(command == 'KEY_STOP'):
                ir_conn.close()
                shutdown()

def shutdown():
    set_diode('yellow')
    subprocess.call(['shutdown', '-h', 'now'], shell=False)

def join_input_threads():
    global threads
    for t in threads:
        print('joining ', t.getName())
        t.join()
    for t in threads:
        threads.remove(t)

def start_input_handling():
    global threads
    t2 = threading.Thread(target = handle_ir_remote, name='ir_thread')
    threads.append(t2)
    t2.start()
    t3 = threading.Thread(target = handle_rotary_encoder, name='rotary_thread')
    threads.append(t3)
    t3.start()
    set_diode('red')
    print('input handling started')

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    # GREEN
    GPIO.setup(17, GPIO.OUT)
    # YELLOW
    GPIO.setup(22, GPIO.OUT)
    # RED
    GPIO.setup(27, GPIO.OUT)

def set_diode(color):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    if(color == 'yellow'):
        GPIO.output(17, GPIO.LOW)
        GPIO.output(22, GPIO.HIGH)
        GPIO.output(27, GPIO.LOW)
    elif(color == 'green'):
        GPIO.output(17, GPIO.HIGH)
        GPIO.output(22, GPIO.LOW)
        GPIO.output(27, GPIO.LOW)
    elif(color == 'red'):
        GPIO.output(17, GPIO.LOW)
        GPIO.output(22, GPIO.LOW)
        GPIO.output(27, GPIO.HIGH)

def main():
    setup_gpio()
    start_radio()

    while True:
        time.sleep(2)
        if is_radio_running():
            join_input_threads()
        elif not is_input_handling_running():
            start_input_handling()
            

if __name__ == '__main__':
    main()