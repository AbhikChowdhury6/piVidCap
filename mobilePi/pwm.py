#mostly copied from stack overflow
import RPi.GPIO as GPIO
import time
import subprocess
from datetime import datetime
import tzlocal
GPIO.setmode(GPIO.BCM)
GPIO.setup(14, GPIO.OUT)
pwm = GPIO.PWM(14,50)

#print("\nPress Ctrl+C to quit \n")
dc = 0
pwm.start(dc)

try:
    while True:
        temp = subprocess.getoutput("vcgencmd measure_temp|sed 's/[^0-9.]//g'")
        if round(float(temp)) >= 70:
            dc = 100
        elif 70 > round(float(temp)) >= 65:
            dc = 85
        elif 65 > round(float(temp)) >= 60:
            dc = 70
        elif 60 > round(float(temp)) >= 50:
            dc = 50
        elif 50 > round(float(temp)) >= 30:
            dc = 25
        elif 30 > round(float(temp)) >= 0:
            dc = 0
        pwm.ChangeDutyCycle(dc)
        print(datetime.now(tzlocal.get_localzone()),"-CPU Temp:",float(temp)," Fan duty cycle:",dc)
        time.sleep(5.0)


except KeyboardInterrupt:
    pwm.stop()
    GPIO.cleanup()
    #print("Ctrl + C pressed -- Ending program")