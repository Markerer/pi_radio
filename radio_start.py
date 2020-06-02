import time
import subprocess
import i2c_lcd
import psutil
import re
import unicodedata
import threading
import collections

current_station = 1
stop_threads = False
title = ""
lcd_width = 20

stations = [
    {
        'name': 'Radio 1',
        'url': 'http://stream7.radio1.hu/high.mp3'
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
    print('audio not running anymore')

def extract_stream_title(cv, process, append):
    global stop_threads
    global title
    global lcd_width
    while(not stop_threads):
        if stop_threads:
            print('stop_extract')
            break
        for line in iter(process.stdout.readline, ''):
            append(line)

            if not line:
                print('not line')
                break
            else:
                matches = re.findall("ICY Info: StreamTitle='([^']*)", str(line))
                if(len(matches) > 0):
                    tmp_title = matches[-1]
                    tmp_title = unicodedata.normalize('NFD', tmp_title)\
                        .encode('ascii', 'ignore')\
                        .decode("utf-8")
                    print(str(tmp_title))
                    tmp_title = str(tmp_title)
                    str_pad = " " * lcd_width
                    with cv:
                        title = str_pad + tmp_title.upper()
                        print('notify')
                        cv.notify()
                else:
                    if title == "":
                        continue
                    else:
                        with cv:
                            title = ""
                            print('notify empty')
                            cv.notify()


def display_station(cv, name):
    global lcd
    global title
    global lcd_width
    global stop_threads
    str_pad = " " * lcd_width
    tmp_title = ""
    while (not stop_threads):
        with cv:
            cv.wait()
            print('consume')
            tmp_title = title
        if stop_threads:
            print('stop_disp')
            break
        for i in range (0, len(tmp_title)):
            lcd.lcd_display_string("%s     %s" %(time.strftime("%Y/%m/%d"), time.strftime("%H:%M")), 1)
            lcd.lcd_display_string(name.upper(), 2)
            lcd_text = tmp_title[i:(i+lcd_width)]
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


def main():
    global stations
    global current_station
    global lcd
    global stop_threads

    lcd = i2c_lcd.lcd()

    process = start_stream(stations[current_station].get('url'))
    condition = threading.Condition()
    num_of_lines = 1
    q = collections.deque(maxlen=num_of_lines)
    t1 = threading.Thread(target=extract_stream_title, args=(condition, process, q.append))
    t1.daemon = True
    t1.start()
    t2 = threading.Thread(target = display_station, args=[condition, get_current_station_name()])
    t2.start()
    time.sleep(20)
    stop_threads = True
    print('thread killed')
    kill(process.pid)
    t1.join()
    t2.join()

if __name__ == '__main__':
    main()
