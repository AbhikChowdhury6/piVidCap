import cv2
import torch
import numpy as np
import gc
from datetime import datetime, timedelta

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
    print(f"vidCap waiting {secondsToWait} till {timedelta(seconds=st + secondsToWait)} to start")
    sys.stdout.flush()
    time.sleep(secondsToWait)

    while True:        
        frameTime = datetime.now().astimezone()

        if subSample == 1:
            ctsb.append(picam2.capture_array(), frameTime.astimezone(ZoneInfo("UTC")))
        else:
            frame = np.ascontiguousarray(picam2.capture_array()[::subSample, ::subSample, :])
            ctsb.append(frame, frameTime.astimezone(ZoneInfo("UTC")))
        
        frameTS = datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")
        cv2.putText(ctsb[ctsb.lastidx()], frameTS, (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, 
                (0, 255, 0), 2, cv2.LINE_AA)

        if exitSignal[0] == 1:
            print("piVidCap got exit signal")
            sys.stdout.flush()
            break

        delayTill100ms()

    cap.release()
    print("piVidCap exiting")
    sys.stdout.flush()