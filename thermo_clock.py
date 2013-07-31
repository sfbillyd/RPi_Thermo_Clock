import os
import glob
import time
import datetime
from Adafruit_7Segment import SevenSegment
import RPi.GPIO as io 
import subprocess
import re
import httplib
import urllib

DEBUG = 1
counter = 0

io.setmode(io.BCM)
#switch_pin = 18
#io.setup(switch_pin, io.IN) 
segment = SevenSegment(address=0x70)
 
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
 
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'
colon = 0
 
def read_temp_raw():
    catdata = subprocess.Popen(['cat',device_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out,err = catdata.communicate()
    out_decode = out.decode('utf-8')
    lines = out_decode.split('\n')
    return lines
 
def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c, temp_f

def display_temp():
    temp = int(read_temp()[1]) # F
    # temp = int(read_temp()[0]) # C
    sign = (temp < 0)
    temp = abs(temp)
    digit_1 = temp % 10
    temp = temp / 10
    digit_2 = temp % 10
    temp = temp / 10
    digit_3 = temp % 10
    segment.setColon(False)
    if sign :
        segment.writeDigitRaw(0, 0x40)       # - sign
    if digit_3 > 0 :
        segment.writeDigit(0, digit_3)       # Hundreds
    else:
        segment.writeDigitRaw(0, 0)
    if digit_2 > 0 :
        segment.writeDigit(1, digit_2)       # Tens
    else:
        segment.writeDigitRaw(1, 0)
    segment.writeDigit(3, digit_1)           # Ones
    segment.writeDigitRaw(4, 0x71) #F        # Temp units letter
    #segment.writeDigitRaw(4, 0x39) #C  
    
def display_time(): 
    global colon
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute
    second = now.second
    # Set hours
    segment.writeDigit(0, int(hour / 10))     # Tens
    segment.writeDigit(1, hour % 10)          # Ones
    # Set minutes
    segment.writeDigit(3, int(minute / 10))   # Tens
    segment.writeDigit(4, minute % 10)        # Ones
    # Toggle colon
    segment.writeDigitRaw(2, 0xFF)    
    # colon = colon ^ 0x2
    
def thingspeak_update():
    temp = int(read_temp()[1]) # F
    # temp = int(read_temp()[0]) # C        
    params = urllib.urlencode({'field1': temp})
    headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/pl$"}
    conn = httplib.HTTPConnection("api.thingspeak.com:80")
    conn.request("POST", "/update?key=#####yourAPIKeyHere###", params, headers)  #replace ###yourAPIKeyHere### with the API from thingspeak--LEAVE the " at the end of the API key
    response = conn.getresponse()
    print response.status, response.reason
    data = response.read()
    conn.close()
    return
    #       time.sleep(30)

def segment_all_off(seg):  # to turn off the display one block at a time
    segment.writeDigitRaw(seg, 0x00) # sends null to passed digit block
    return
def segment_all_on(seg):  # illuminates all segments of an individual block (including the dots)
    if seg == 2:
	segment.writeDigitRaw(seg, 0xFF) # toggles colon to on
    else:
        segment.writeDigitRaw(seg, 0xFF) # sends all on to passed digit block
    return

def all_blocks_off():  # sends null to each digit block and colon (useful to turn off display after cntrl-c abort
	for blocks in range(0,5):
		segment.writeDigitRaw(blocks, 0x00) 
    
	
def LED_Check(num_loops):  # for effect it cycles through each digit block in rapid succession
    counter = 0
    delay = 0.025
    while (counter < num_loops):
    	for seg in range(0,5):  # flash each block in rapid succession left to right
	    segment_all_on(seg)
            time.sleep(delay)
            segment_all_off(seg)
            time.sleep(delay)

        for seg in range (4,-1,-1):  # flash each block in rapid succession right to left
            segment_all_on(seg)
	    time.sleep(delay)
	    segment_all_off(seg)
	    time.sleep(delay)
        
        counter += 1
	# time.sleep(.5)

    
	
try:
    LED_Check(5)

    while True: 
    #   if io.input(switch_pin): ### This commented section relates to the use of a physical switch to change what is displayed.
    #       display_temp()
    #   else :
    #       display_time()
    #   time.sleep(0.5)
        if counter < 30:              # for 30 seconds toggle between time and temp and at the end send the temp to thingspeak
            if counter % 5 == 0:
                display_time()
                # print counter
                counter = counter + 1
                time.sleep(0.5)
            else:
                display_temp()
                # print counter
                counter = counter + 1
	        time.sleep(0.5)
        else:
            counter = 0
            print counter
            thingspeak_update()           # this is where we call the function to send the current temp to thingspeak
            print datetime.datetime.now()  # debug to the terminal to show things are working
            time.sleep(0.5)

except KeyboardInterrupt:
    all_blocks_off()

