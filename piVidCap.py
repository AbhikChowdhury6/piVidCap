from picamera2 import Picamera2
import cv2
import torch
import numpy as np
import os
import sys
import gc
from datetime import datetime, timedelta
import time
from zoneinfo import ZoneInfo


repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")
from circularTimeSeriesBuffer import CircularTimeSeriesBuffer
if os.path.exists(repoPath + "piVidCap/deviceInfo.py"):
    from deviceInfo import subSample
else:
    subSample = 3 #default to 480p ish


def pi_vid_cap(ctsb: CircularTimeSeriesBuffer, exitSignal):
    """ Captures frames and writes to the shared buffer in a circular fashion. """
    st = datetime.now() 
    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(main={"size": (1920, 1080), "format": "RGB888"})
    picam2.configure(video_config)
    picam2.start()
    print(f"The cap took {datetime.now()  - st} to initialize")

    st = datetime.now()
    frame = picam2.capture_array()
    print(f"The first Frame took {datetime.now() - st} to capture")
    del frame
    gc.collect()
    
    def delayTill100ms(): # a bit offset to compensate for read lag
        msToDelay = 100 - ((datetime.now().microsecond / 1000) % 100)
        time.sleep(msToDelay/1000)

    st = datetime.now()
    secondsToWait = (14 - (st.second % 15)) + (1 - st.microsecond/1_000_000)
    print(f"vidCap waiting {secondsToWait} till {st + timedelta(seconds=secondsToWait)} to start")
    sys.stdout.flush()
    time.sleep(secondsToWait)

    while True:
        if exitSignal[0] == 1:
            print("piVidCap got exit signal")
            sys.stdout.flush()
            break

        print("going to get frame")
        frameTime = datetime.now().astimezone()
        if subSample == 1:
            frame = picam2.capture_array()
        else:
            frame = np.ascontiguousarray(picam2.capture_array()[::subSample, ::subSample, :])
            
        frameTS = datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")
        cv2.putText(frame, frameTS, (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, 
                (0, 255, 0), 2, cv2.LINE_AA)
        print("frame is captured and written on")

        print(f"nextidx from piVidCap is {ctsb.nextidx[0]} before append")
        ctsb.append(frame, frameTime.astimezone(ZoneInfo("UTC")))
        print(f"nextidx from piVidCap is {ctsb.nextidx[0]} after append")

        #manually set
        #ctsb[ctsb.nextidx] = frame
        #print(f"nextidx from piVidCap is {ctsb.nextidx} before append")
        #ctsb.nextidx += 1
        #print(f"nextidx from piVidCap is {ctsb.nextidx} after append")
        

        delayTill100ms()

    print("piVidCap exiting")
    sys.stdout.flush()