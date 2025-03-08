import cv2
import torch
from datetime import datetime, timedelta
import pandas as pd
import os
import sys
import time
import numpy as np

repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")
from circularTimeSeriesBuffer import CircularTimeSeriesBuffer

if os.path.exists(repoPath + "piVidCap/deviceInfo.py"):
    from deviceInfo import deviceInfo
else:
    from collections import OrderedDict
    keys = ["responsiblePartyName", "instanceName", "developingPartyName", "deviceName", "dataType", "dataSource"]
    values = ["abhik", "notSet", "abhik", "unknown", "mp4", "piVidCap"]
    deviceInfo = OrderedDict(zip(keys, values))

deviceName = "_".join(deviceInfo.values())
if deviceInfo["instanceName"] == "notSet":
    print("no instance name set")
    sys.stdout.flush()
print(f"device name is {deviceName}")
sys.stdout.flush()

user = os.getenv("USER", "pi")
baseFilePath = "/home/" + user + "/Documents/collectedData/" + \
                deviceName + "_"


def writer_worker(ctsb: CircularTimeSeriesBuffer, personSignal, exitSignal):
    print("in writer worker")
    sys.stdout.flush()
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    frameWidthHeight = (0,0)
    def dt_to_fnString(dt):
        return dt.astimezone(ZoneInfo("UTC")).strftime('%Y-%m-%dT%H%M%S,%f%z')
    
    def exitVideo(output, tsList, tempFilePath):
        output.release()

        # rename video
        fbfn = baseFilePath + tsList[0].strftime('%Y-%m-%d%z') + "/"
        fbfn += dt_to_fnString(tsList[0]) + "_" + dt_to_fnString(titsListmestamps[-1])
        os.rename(tempFilePath, fbfn + ".mp4")
        
        # write timestamps 
        tsdf = pd.DataFrame(data=tsList, columns=['sampleDT'])
        tsdf = tsdf.set_index('sampleDT')
        tsdf.to_parquet(fbfn + ".parquet.gzip", compression='gzip')

        print(f"finished writing the file {tempFilePath}")
        return []

    def startNewVideo(tsList, tempFilePath):
        os.makedirs(tempFilePath[:-7], exist_ok=True)
        if os.path.exists(tempFilePath):
                os.remove(tempFilePath)
        
        output = cv2.VideoWriter(tempFilePath, 
                        fourcc, 
                        30.0, 
                        frameWidthHeight)
        
        return output
        

    model_result = False
    timestamps = []
    first = True
    tryStartNewVideo = True
    while True:
        if exitSignal[0] == 1:
            print("writer worker got exit signal")
            sys.stdout.flush()
            timestamps = exitVideo(output, timestamps, tempFilePath)
            break
        
        # wait till a round 15 seconds and then
        st = datetime.now()
        secondsToWait = (14 - (st.second % 15)) + (1 - st.microsecond/1_000_000)
        print(f" writer waiting {secondsToWait} till {st + timedelta(seconds=secondsToWait)}")
        time.sleep(secondsToWait)
        
        
        # check if we want to save the last 30, 15 seconds or 1 frame
        last_mr = model_result
        model_result = personSignal[0]
        if model_result and not last_mr:
            print("writing last 30 secs")
            newFrames, newTimestamps = ctsb.get_last_30_seconds()

        elif model_result or last_mr:
            print("writing last 15 secs")
            newFrames, newTimestamps = ctsb.get_last_15_seconds()

        else:
            print("writing only 30s old frame")
            newFrames, newTimestamps = ctsb.get_last_30_seconds()
            if len(newTimestamps) > 0:
                newFrames = [newFrames[0]]
                newTimestamps = [newTimestamps[0]]
        

        print(f"len of new timestamps in writer {len(newTimestamps)}")
        print(f"len of timestamps {len(timestamps)}")
        sys.stdout.flush()
        if len(newTimestamps) == 0:
            continue


        # initialize stream parameters if we haven't
        if first:
            first = False    
            frameWidthHeight = (newFrames[0].shape[1], newFrames[0].shape[0])
        
        # check if we have to make a new file
        if tryStartNewVideo:
            tryStartNewVideo = False
            tempFilePath = baseFilePath + newTimestamps[0].strftime('%Y-%m-%d%z') + "/new.mp4"
            output = startNewVideo(newTimestamps, tempFilePath)

        # if crosses midnight close the file and start a new one
        if len(timestamps) == 0:
            firstTimestamp = newTimestamps[0]
        else:
            firstTimestamp = timestamps[0]
        
        if firstTimestamp.day < newTimestamps[-1].day:
            print(f"crossed midnight!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            sys.stdout.flush()

            cutoffFrameIndex = len(newFrames)
            while firstTimestamp.day < newTimestamps[cutoffFrameIndex-1].day:
                cutoffFrameIndex -= 1
            cutoffFrameIndex -= 1

            # write and exit the previous days video
            for frame in newFrames[:cutoffFrameIndex]:
                frame = frame.cpu().numpy()  # Convert from torch tensor to numpy
                frame = frame.astype(np.uint8)
                output.write(frame)
            timestamps.extend(newTimestamps[:cutoffFrameIndex])
            timestamps = exitVideo(output, timestamps, tempFilePath)

            # start and write the new day
            timestamps.extend(newTimestamps[cutoffFrameIndex:])
            tempFilePath = baseFilePath + timestamps[0].strftime('%Y-%m-%d%z') + "/new.mp4"
            output = startNewVideo(timestamps, tempFilePath)
            for frame in newFrames[cutoffFrameIndex:]:
                frame = frame.cpu().numpy()  # Convert from torch tensor to numpy
                frame = frame.astype(np.uint8)
                output.write(frame)
        
        else:
            # else just add to the file
            st = datetime.now()
            for frame in newFrames:
                frame = frame.cpu().numpy()  # Convert from torch tensor to numpy
                frame = frame.astype(np.uint8)
                output.write(frame)
            timestamps.extend(newTimestamps)
            numAddedFrames += len(newFrames)
            print(f"have {numAddedFrames} frames in the current video")
            print(f"it took {datetime.now() - st} to write the frames")
            sys.stdout.flush()

            # check if the file is too big and close it if it is
            if len(timestamps) >= 1800:
                timestamps = exitVideo(output, timestamps, tempFilePath)
                tryStartNewVideo = True
        
        



    print("writer worker exiting")
    sys.stdout.flush()
