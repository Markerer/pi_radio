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

current_station = 1
stop_threads = False
stop_all = False
title = ""
lcd_width = 20
process = 0
threads = []

stations = [
    {
        'name': 'Radio 1',
        'url': 'http://stream1.radio1.hu/high.mp3'
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
        'name': 'Sunshine radio',
        'url': 'http://195.56.193.129:8100/;stream.nsv#.mp3'
    },
    {
        'name': 'Megadance',
        'url': 'https://cloudfront41.lexanetwork.com:8080/livemega.mp3'
    },
    {
        'name': 'Retro radio',
        'url': 'https://stream.retroradio.hu/high.mp3'
    },
    {
        'name': 'Jolly radio',
        'url': 'http://stream.mercyradio.eu/jolly.mp3'
    }
]

def kill(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()
    print('audio processes killed')

def stop_all_threads():
    global threads
    global stop_all
    global stop_threads
    global process
    stop_all = True
    stop_threads = True
    kill(process.pid)
    for t in threads:
        print('joining %s ', t.getName())
        t.join()

def stop_some_threads():
    global threads
    global stop_threads
    global process
    stop_threads = True
    for t in threads:
        if((t.getName() == 'extract_thread') or (t.getName() == 'display_thread')):
            print('joining %s ', t.getName())
            t.join()
            threads.remove(t)
    strop_threads = False

def extract_stream_title(cv, append):
    global title
    global lcd_width
    global stop_threads
    global process
    while(not stop_threads):
        if stop_threads:
            print('stop_extract')
            break
        for line in iter(process.stdout.readline, ''):
            append(line)

            if not line:
                print('could not read line')
                time.sleep(1)
                break
            else:
                print(line)
                matches = re.findall("ICY Info: StreamTitle='([^']*)", line.decode('utf-8'))
                if(len(matches) > 0):
                    tmp_title = unidecode.unidecode(matches[-1])
                    print(tmp_title)
                    str_pad = " " * lcd_width
                    title = str_pad + tmp_title.upper()

def display_station(cv, name):
    global lcd
    global title
    global lcd_width
    global stop_threads
    str_pad = " " * lcd_width
    tmp_title = ""
    while (not stop_threads):
        if stop_threads:
            print('stop_disp')
            break
        for i in range (0, len(title)):
            lcd.lcd_display_string("%s     %s" %(time.strftime("%Y/%m/%d"), time.strftime("%H:%M")), 1)
            lcd.lcd_display_string(name.upper(), 2)
            lcd_text = title[i:(i+lcd_width)]
            lcd.lcd_display_string(lcd_text,3)
            time.sleep(0.5)
            lcd.lcd_display_string(str_pad,3)

def start_stream(url, process=None):
    if not (process is None):
        kill(process.pid)
    args = ['mplayer', url]
    proc = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE)
    return proc

def get_current_station_name():
    global stations
    global current_station
    return stations[current_station].get('name')

def switch_station():
    global stations
    global current_station
    global process
    process = start_stream(stations[current_station].get('url'), process)

def handle_rotary_encoder():
    global stop_all
    CLOCKPIN = 7
    DATAPIN = 8
    SWITCHPIN = 25
    ky040 = KY040(CLOCKPIN, DATAPIN, SWITCHPIN, rotaryChange, switchPressed, rotaryBouncetime=25, switchBouncetime=750)
    ky040.start()
    try:
        while(not stop_all):
            time.sleep(0.1)
    finally:
        ky040.stop()
        GPIO.cleanup()

def rotaryChange(direction):
    global current_station
    global stations
    global threads
    print('current_station before: ', current_station)
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
    print('current_station after: ', current_station)
    switch_station()
    stop_some_threads()

    condition = threading.Condition()
    num_of_lines = 1
    q = collections.deque(maxlen=num_of_lines)
    t1 = threading.Thread(target=extract_stream_title, args=[condition, q.append], name='extract_thread')
    t1.daemon = True
    threads.append(t1)
    t1.start()
    t2 = threading.Thread(target = display_station, args=[condition, get_current_station_name()], name='display_thread')
    threads.append(t2)
    t2.start()


def switchPressed():
    print('switch pressed')
    stop_all_threads()

def main():
    global stations
    global current_station
    global lcd
    global process
    global threads

    lcd = i2c_lcd.lcd()
    process = start_stream(stations[current_station].get('url'))
    condition = threading.Condition()
    num_of_lines = 1
    q = collections.deque(maxlen=num_of_lines)
    t1 = threading.Thread(target=extract_stream_title, args=[condition, q.append], name='extract_thread')
    t1.daemon = True
    threads.append(t1)
    t1.start()
    t2 = threading.Thread(target = display_station, args=[condition, get_current_station_name()], name='display_thread')
    threads.append(t2)
    t2.start()
    t3 = threading.Thread(target = handle_rotary_encoder)
    threads.append(t3)
    t3.start()

if __name__ == '__main__':
    main()
