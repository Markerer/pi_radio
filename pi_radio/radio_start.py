import time
import subprocess
import i2c_lcd
import psutil
import re
import unidecode
import threading
import collections
import RPi.GPIO as GPIO
from ky040.KY040 import KY040
import alsaaudio
from lirc import RawConnection
import logging
from datetime import datetime

mixer = alsaaudio.Mixer('SoftMaster')

last_volume = 100

current_station = 0
stop_threads = False
stop_all = False
title = ""
lcd_width = 20
process = 0
threads = []
display_step = 2

ir_conn = RawConnection()

stations = [
    {
        'name': 'Radio 1',
        'url': 'https://icast.connectmedia.hu/5201/live.mp3'
    },
    {
        'name': 'Szunet radio',
        'url': 'http://92.61.114.191:1101/;'
    },
    {
        'name': 'Petofi radio',
        'url': 'http://mr-stream.mediaconnect.hu/4738/mr2.mp3'
    },
    {
        'name': 'Megadance',
        'url': 'http://megadanceradio.hopto.org:8000/livemega.mp3'
    },
    {
        'name': 'Retro radio',
        'url': 'http://stream1.retroradio.hu/high.mp3'
    },
    {
        'name': 'KISS FM - Beats',
        'url': 'http://topradio-de-hz-fal-stream02-cluster01.radiohost.de/kissfm-pure_mp3-192'
    },
    {
        'name': 'BEST FM Debrecen',
        'url': 'http://stream.webthings.hu:8000/fm95-x-128.mp3'
    }
]

def kill(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()
    logging.info(f'Process with pid: {proc_pid} has been killed')

def stop_all_threads():
    global threads
    global stop_all
    global stop_threads
    global lcd
    global process
    stop_all = True
    stop_threads = True
    for t in threads:
        if(t.getName() != 'rotary_thread' and t.getName() != 'ir_remote_thread' and t.getName() != 'extract_thread'):
            logging.info(f'Joining {t.getName()} thread')
            t.join()
    for t in threads:
        if(t.getName() != 'rotary_thread' and t.getName() != 'ir_remote_thread'):
            threads.remove(t)

    lcd.lcd_clear()
    lcd.backlight(0)
    ir_conn.close()
    kill(process.pid)
    # subprocess.call(['shutdown', '-h', 'now'], shell=False)

# Stopping all necessary threads when changing channels
def stop_some_threads():
    global threads
    global stop_threads
    stop_threads = True
    threads_to_remove = []
    for t in threads:
        if((t.getName() == 'display_thread')):
            logging.info(f'Joining {t.getName()} thread')
            threads_to_remove.append(t)
            t.join()
    for tr in threads_to_remove:
        if tr in threads:
            threads.remove(tr)
    logging.info(f'From {len(threads)} threads {len(threads_to_remove)} have been removed')
    stop_threads = False

# Infinite loop for extracting stream title
def extract_stream_title():
    global title
    global lcd_width
    global process
    global stop_threads
    while True:
        if stop_threads:
            logging.info('Stopping extract thread from extract root')
            break
        time.sleep(1.0)
        for line in process.stdout:
            if stop_threads:
                logging.info('Stopping extract thread from extract for cycle')
                break
            logging.info(line)
            decoding_finished = re.findall("Decoding of (.*) finished.", line.decode('UTF-8'))
            if(len(decoding_finished) > 0):
                logging.error('Decoding finished, restarting audio process.')
                switch_station()
            matches = re.findall("ICY-META: StreamTitle='(.*?(?=\\';))", line.decode('UTF-8'))
            if(len(matches) > 0):
                logging.info(matches[0])
                tmp_title = matches[0].upper()
                tmp_title = tmp_title.replace('Á', 'A').replace('Ú', 'U').replace('Ű', 'U').replace('É', 'E').replace('Ó', 'O').replace('Ü', 'U').replace('Ö', 'O').replace('Ő', 'O').replace("'", '').replace('.', '')
                tmp_title = unidecode.unidecode(tmp_title)
                logging.info(tmp_title)
                str_pad = " " * lcd_width
                title = str_pad + tmp_title.upper()

# Infinite loop for displaying actual station and information
def display_station(name):
    global lcd
    global title
    global lcd_width
    global current_station
    global display_step
    str_pad = " " * lcd_width
    str_pad_station = (lcd_width - len(name) - 2) * " "
    while True:
        global stop_threads
        if stop_threads:
            logging.info('Stopping display thread from display root')
            lcd.lcd_clear()
            break
        time.sleep(1.0)
        i = 0
        while i < len(title):
            if stop_threads:
                logging.info('Stopping display thread from display for cycle')
                break
            lcd.lcd_display_string("%s     %s" %(time.strftime("%Y/%m/%d"), time.strftime("%H:%M")), 1)
            lcd.lcd_display_string(name.upper() + str_pad_station + str(current_station + 1).zfill(2), 2)
            lcd_text = title[i:(i+lcd_width)]
            lcd.lcd_display_string(lcd_text,3)
            time.sleep(0.5)
            lcd.lcd_display_string(str_pad,3)
            current_volume = 'HANGERO: ' + str(mixer.getvolume()[0])
            str_pad_volume = (lcd_width - len(current_volume)) * " "
            lcd.lcd_display_string(current_volume + str_pad_volume, 4)
            i += display_step

def start_stream(url, process=None):
    if not (process is None):
        kill(process.pid)
    args = ['mpg123', '-y', url, '--utf8', '--long-tag', '--timeout 5']
    proc = subprocess.Popen(args, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    logging.info(f'Starting process with pid: {proc.pid}')
    return proc

def get_current_station_name():
    global stations
    global current_station
    return stations[current_station].get('name')

def get_current_station_url():
    global stations
    global current_station
    return stations[current_station].get('url')

def switch_station():
    global process
    process = start_stream(get_current_station_url(), process)

def increase_display_step():
    global display_step
    if(display_step < 5):
        display_step += 1
        logging.info(f'Display step set to {display_step}')

def decrease_display_step():
    global display_step
    if(display_step > 1):
        display_step -= 1
        logging.info(f'Display step set to {display_step}')

# Infinite loop for IR remote handling
def handle_ir_remote():
    global ir_conn
    global stop_all
    #get IR command
    #keypress format = (hexcode, repeat_num, command_key, remote_id)
    while True:
        if stop_all:
            logging.info('Stopping IR thread')
            break
        try:
            keypress = ir_conn.readline(.0001)
        except:
            keypress=""

        time.sleep(0.25)
        
        if (keypress != "" and keypress != None):
                    
            data = keypress.split()
            sequence = data[1]
            command = data[2]
            
            #ignore command repeats
            if (sequence != "00"):
                continue
            
            if(command == 'skip_back'):
                logging.info('IR SKIP_BACK key pressed')
                rotaryChange(0)
                time.sleep(0.5)
            elif(command == 'skip_forward'):
                logging.info('IR SKIP_FORWARD key pressed')
                rotaryChange(1)
                time.sleep(0.5)
            elif(command == 'KEY_POWER'):
                logging.info('IR POWER key pressed')
                stop_all_threads()
            elif(command == 'KEY_REWIND'):
                logging.info('IR REWIND key pressed')
                decrease_display_step()
                time.sleep(0.5)
            elif(command == 'KEY_FASTFORWARD'):
                logging.info('IR FASTFORWARD key pressed')
                increase_display_step()
                time.sleep(0.5)
            
# Infinite loop for rotary encoder (for channel switch)
def handle_rotary_encoder():
    CLOCKPIN = 7
    DATAPIN = 8
    SWITCHPIN = 10
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(CLOCKPIN, GPIO.IN)
    GPIO.setup(DATAPIN, GPIO.IN)
    GPIO.setup(SWITCHPIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(CLOCKPIN, GPIO.FALLING, bouncetime=50)
    GPIO.add_event_detect(SWITCHPIN, GPIO.FALLING, bouncetime=750)
    try:
        while True:
            global stop_all
            GPIO.setmode(GPIO.BCM)
            if stop_all:
                break
            time.sleep(0.15)
            if GPIO.event_detected(CLOCKPIN):
                GPIO.remove_event_detect(CLOCKPIN)
                if GPIO.input(CLOCKPIN) == 0:
                    data = GPIO.input(DATAPIN)
                    if data == 1:
                        rotaryChange(1)
                    else:
                        rotaryChange(0)
                time.sleep(0.5)
                GPIO.add_event_detect(CLOCKPIN, GPIO.FALLING, bouncetime=50)
            if GPIO.event_detected(SWITCHPIN):
                if GPIO.input(SWITCHPIN) == 0:
                    switchPressed()
    finally:
        GPIO.setmode(GPIO.BCM)
        GPIO.remove_event_detect(CLOCKPIN)
        GPIO.remove_event_detect(DATAPIN)
        GPIO.remove_event_detect(SWITCHPIN)
        time.sleep(5)

# Infinite loop for rotary encoder (for volume switch)
def handle_volume_rotary_encoder():
    CLOCKPIN = 5
    DATAPIN = 6
    SWITCHPIN = 13
    volky040 = KY040(CLOCKPIN, DATAPIN, SWITCHPIN, rotaryVolumeChange, volumeSwitchPressed, rotaryBouncetime=25, switchBouncetime=750)
    volky040.start()
    try:
        while True:
            global stop_all
            if stop_all:
                break
            time.sleep(0.15)
    finally:
        volky040.stop()
        GPIO.cleanup()

# Callback for rotary encoder change (for volume switch)
def rotaryVolumeChange(direction):
    current_volume = mixer.getvolume()[0]
    if(direction == 0 and current_volume >= 5):
        mixer.setvolume(current_volume - 5)
    if(direction == 1 and current_volume <= 95):
        mixer.setvolume(current_volume + 5)
    logging.info(f'Current_volume: {current_volume}')
    logging.info(f'New value: {mixer.getvolume()[0]}')

# Callback for switch button pressed
def volumeSwitchPressed():
    global last_volume
    current_volume = mixer.getvolume()[0]
    if(current_volume != 0):
        mixer.setvolume(0)
        last_volume = current_volume
        logging.info('Muted')
    else:
        mixer.setvolume(last_volume)
        logging.info('Unmuted')

# Callback for rotary encoder change (for station switch)
def rotaryChange(direction):
    global current_station
    global stations
    global threads
    logging.info(f'current_station before: {current_station}')
    if(direction == 0):
        if(current_station > 0):
            current_station -= 1
        else:
            current_station = len(stations) - 1
    else:
        if(current_station + 1 < len(stations)):
            current_station += 1
        else:
            current_station = 0
    logging.info(f'current_station after: {current_station}')
    stop_some_threads()
    switch_station()

    t1 = threading.Thread(target=extract_stream_title, name='extract_thread')
    t1.daemon = True
    threads.append(t1)
    t1.start()
    t2 = threading.Thread(target = display_station, args=[get_current_station_name()], name='display_thread')
    threads.append(t2)
    t2.start()

# Callback for rotary switch press (on station switch encoder)
def switchPressed():
    logging.info('Rotary switch pressed, shutting down python process')
    stop_all_threads()

# Starting all processes, setting up logging
def main():
    global lcd
    global process
    global threads

    now = datetime.now().strftime('%Y_%m_%d_%H%M%S')
    logging.basicConfig(filename='/home/pi/logs/radio_log_' + now + '.log',
     level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    lcd = i2c_lcd.lcd()
    process = start_stream(get_current_station_url())
    t1 = threading.Thread(target=extract_stream_title, name='extract_thread')
    t1.daemon = True
    threads.append(t1)
    t1.start()
    t2 = threading.Thread(target = display_station, args=[get_current_station_name()], name='display_thread')
    threads.append(t2)
    t2.start()
    t3 = threading.Thread(target = handle_rotary_encoder, name='rotary_thread')
    threads.append(t3)
    t3.start()
    t4 = threading.Thread(target = handle_volume_rotary_encoder, name='rotary_volume_thread')
    threads.append(t4)
    t4.start()
    t5 = threading.Thread(target = handle_ir_remote, name='ir_remote_thread')
    threads.append(t5)
    t5.start()

if __name__ == '__main__':
    main()
