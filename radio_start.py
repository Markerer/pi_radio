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

mixer = alsaaudio.Mixer('SoftMaster')

last_volume = 100

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
        'url': 'http://megadanceradio.hopto.org:8000/livemega.mp3'
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
    global lcd
    global process
    stop_all = True
    stop_threads = True
    for t in threads:
        print('joining ', t.getName())
        if(t.getName() != 'rotary_thread'):
            t.join()
    for t in threads:
        if(t.getName() != 'rotary_thread'):
            threads.remove(t)

    lcd.lcd_clear()
    lcd.backlight(0)
    kill(process.pid)
    threads[0].join()
    subprocess.call(['shutdown', '-h', 'now'], shell=False)

def stop_some_threads():
    global threads
    global stop_threads
    global process
    stop_threads = True
    for t in threads:
        if((t.getName() == 'extract_thread') or (t.getName() == 'display_thread')):
            print('joining ', t.getName())
            t.join()
    for t in threads:
        if((t.getName() == 'extract_thread') or (t.getName() == 'display_thread')):
            threads.remove(t)
    stop_threads = False

def send_empty_message_periodically():
    global process
    try:
        while True:
            global stop_all
            if stop_all:
                print('stop_msg')
                break
            poll = process.poll()
            if poll == None:
                process.stdin.write(b'123\n')
            time.sleep(1)
    finally:
        poll = process.poll()
        if poll == None:
            process.stdin.close()

def extract_stream_title():
    global title
    global lcd_width
    global process
    while True:
        global stop_threads
        if stop_threads:
            print('stop_extract')
            break
        for line in iter(process.stdout.readline, ''):
            if stop_threads:
                print('stop_extract')
                break

            if not line:
                print('could not read line')
                time.sleep(1)
                break
            else:
                print(line)
                matches = re.findall("ICY Info: StreamTitle='([^']*)", line.decode('ISO-8859-2'))
                if(len(matches) > 0):
                    tmp_title = tmp_title.upper()
                    tmp_title = tmp_title.replace('Á', 'A').replace('Ú', 'U').replace('Ű', 'U').replace('É', 'E').replace('Ó', 'O').replace('Ü', 'U').replace('Ö', 'O').replace('Ő', 'O')
                    tmp_title = unidecode.unidecode(matches[-1])
                    print(tmp_title)
                    str_pad = " " * lcd_width
                    title = str_pad + tmp_title.upper()

def display_station(name):
    global lcd
    global title
    global lcd_width
    str_pad = " " * lcd_width
    str_pad_station = (lcd_width - len(name)) * " "
    while True:
        global stop_threads
        if stop_threads:
            print('stop_disp')
            break
        for i in range (0, len(title)):

            if stop_threads:
                print('stop_disp')
                break
            lcd.lcd_display_string("%s     %s" %(time.strftime("%Y/%m/%d"), time.strftime("%H:%M")), 1)
            lcd.lcd_display_string(name.upper() + str_pad_station, 2)
            lcd_text = title[i:(i+lcd_width)]
            lcd.lcd_display_string(lcd_text,3)
            time.sleep(0.5)
            lcd.lcd_display_string(str_pad,3)
            current_volume = 'HANGERO: ' + str(mixer.getvolume()[0])
            str_pad_volume = (lcd_width - len(current_volume)) * " "
            lcd.lcd_display_string(current_volume + str_pad_volume, 4)

def start_stream(url, process=None):
    if not (process is None):
        kill(process.pid)
    args = ['mplayer', url]
    proc = subprocess.Popen(args, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
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
    CLOCKPIN = 7
    DATAPIN = 8
    SWITCHPIN = 3
    ky040 = KY040(CLOCKPIN, DATAPIN, SWITCHPIN, rotaryChange, switchPressed, rotaryBouncetime=75, switchBouncetime=750)
    ky040.start()
    try:
        while True:
            global stop_all
            if stop_all:
                break
            time.sleep(0.1)
    finally:
        ky040.stop()
        time.sleep(5)

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
            time.sleep(0.1)
    finally:
        volky040.stop()
        GPIO.cleanup()

def rotaryVolumeChange(direction):
    current_volume = mixer.getvolume()[0]
    if(direction == 0 and current_volume >= 5):
        mixer.setvolume(current_volume - 5)
    if(direction == 1 and current_volume <= 95):
        mixer.setvolume(current_volume + 5)
    print('Current_volume: ', current_volume)
    print('New value: ', mixer.getvolume())

# Callback for switch button pressed
def volumeSwitchPressed():
    global last_volume
    current_volume = mixer.getvolume()[0]
    if(current_volume > 0):
        mixer.setvolume(0)
        last_volume = current_volume
        print('Muted')
    else:
        mixer.setvolume(last_volume)
        print('Unmuted')

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

    t1 = threading.Thread(target=extract_stream_title, name='extract_thread')
    threads.append(t1)
    t1.start()
    t2 = threading.Thread(target = display_station, args=[get_current_station_name()], name='display_thread')
    threads.append(t2)
    t2.start()

def alibi(sleeptime):
    time.sleep(sleeptime)

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
    t1 = threading.Thread(target=extract_stream_title, name='extract_thread')
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
    t5 = threading.Thread(target = send_empty_message_periodically, name='empty_message_thread')
    threads.append(t5)
    t5.start()

if __name__ == '__main__':
    main()
