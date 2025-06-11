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
import tzlocal
from logUtils import worker_configurer
import logging

repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")
from circularTimeSeriesBuffer import CircularTimeSeriesBuffers
if os.path.exists(repoPath + "piVidCap/deviceInfo.py"):
    from deviceInfo import subSample, buffSecs, capHz, maxWidth, maxHeight, rotate
else:
    print("error no deviceInfo found")
    sys.exit()


def pi_vid_cap(ctsb: CircularTimeSeriesBuffers, exitSignal, debugLvl, log_queue):
    worker_configurer(log_queue)
    l = logging.getLogger("pi_vid_cap_worker")
    l.info("vid cap worker started")


    """ Captures frames and writes to the shared buffer in a circular fashion. """
    st = datetime.now() 
    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(main={"size": (maxWidth, maxHeight), "format": "RGB888"})
    picam2.configure(video_config)
    picam2.start()
    l.debug("The cap took %s to initialize", str(datetime.now()  - st))

    st = datetime.now()
    frame = picam2.capture_array()
    l.debug("The first Frame took %s to capture", str(datetime.now()  - st))
    st = datetime.now()
    frame = picam2.capture_array()
    l.debug("The second Frame took %s to capture", str(datetime.now()  - st))
    del frame
    gc.collect()
    
    def delayTillHzms(): # a bit offset to compensate for read lag
        msToDelay = (1000/capHz) - ((datetime.now().microsecond / 1000) % (1000/capHz))
        time.sleep(msToDelay/1000)

    st = datetime.now()
    secondsToWait = ((buffSecs-1) - (st.second % buffSecs)) + (1 - st.microsecond/1_000_000)
    l.debug("waiting %d till %s", secondsToWait, str(st + timedelta(seconds=secondsToWait)))
    time.sleep(secondsToWait)

    while True:
        if exitSignal[0] == 1:
            l.info("piVidCap got exit signal")
            break

        #print("going to get frame")
        frameTime = datetime.now().astimezone()
        if subSample == 1:
            frame = picam2.capture_array()
        else:
            frame = np.ascontiguousarray(picam2.capture_array()[::subSample, ::subSample, :])

        if rotate == 1:
            frame = cv2.rotate(frame, rotate)
            
        frameTS = datetime.now(tzlocal.get_localzone()).strftime("%Y-%m-%d %H:%M:%S%z")
        cv2.putText(frame, frameTS, (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, 
                (0, 255, 0), 2, cv2.LINE_AA)
        #print("frame is captured and written on")
        #print(frameTS)

        # #print(f"nextidx from piVidCap is {ctsb.nextidx[0]} before append")
        ctsb.append(frame, frameTime.astimezone(ZoneInfo("UTC")))
        #print(f"nextidx from piVidCap is {ctsb.nextidx[0]} after append")

        #manually set
        #ctsb[ctsb.nextidx] = frame
        #print(f"nextidx from piVidCap is {ctsb.nextidx} before append")
        #ctsb.nextidx += 1
        #print(f"nextidx from piVidCap is {ctsb.nextidx} after append")
        

        delayTillHzms()

    l.info("piVidCap exiting")