import i2c_lcd
import time

lcd = i2c_lcd.lcd()
str_pad = " " * 20
my_long_string = "in progress..."
my_long_string = my_long_string.upper()
my_long_string = str_pad + my_long_string

while True:
    for i in range (0, len(my_long_string)):
        lcd_text = my_long_string[i:(i+20)]
        lcd.lcd_display_string(lcd_text,3)
        time.sleep(0.75)
        lcd.lcd_display_string(str_pad,3)
        lcd.lcd_display_string("%s     %s" %(time.strftime("%Y/%m/%d"), time.strftime("%H:%M")), 1)
