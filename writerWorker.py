import cv2
import torch
from datetime import datetime, timedelta, timezone
import pandas as pd
import os
import sys
import time
import numpy as np
from zoneinfo import ZoneInfo

repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")
from circularTimeSeriesBuffer import CircularTimeSeriesBuffers

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


def writer_worker(ctsb: CircularTimeSeriesBuffers, personSignal, exitSignal):
    print("in writer worker")
    sys.stdout.flush()
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    frameWidthHeight = (0,0)
    def dt_to_fnString(dt):
        return dt.astimezone(ZoneInfo("UTC")).strftime('%Y-%m-%dT%H%M%S,%f%z')
    
    def exitVideo(output, tsList, tempFilePath):
        if output is None:
            print("output is None")
            return
        output.release()

        # rename video
        fbfn = baseFilePath + tsList[0].strftime('%Y-%m-%d%z') + "/"
        fbfn += dt_to_fnString(tsList[0]) + "_" + dt_to_fnString(tsList[-1])
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
        
        print("starting a new output")
        print(tempFilePath)
        output = cv2.VideoWriter(tempFilePath, 
                        fourcc, 
                        30.0, 
                        frameWidthHeight)
        
        return output

    def intTensorToDtList(tensor):
        return [datetime.fromtimestamp(ts_ns.item() / 1e9, tz=timezone.utc) for ts_ns in tensor]
        

    model_result = False
    timestamps = []
    first = True
    tryStartNewVideo = True
    output = None
    tempFilePath = None
    while True:
        if exitSignal[0] == 1:
            print("writer worker got exit signal")
            sys.stdout.flush()
            timestamps = exitVideo(output, timestamps, tempFilePath)
            break

        def writeCtsbBufferNum(bufferNum, onlyFirst=False):
            print("using bufferNum", bufferNum)
            nonlocal first
            nonlocal tryStartNewVideo
            nonlocal timestamps
            nonlocal output
            nonlocal tempFilePath

            if ctsb.nextidxs[bufferNum][0] == 0:
                return
            
            if onlyFirst:
                ctsb.time_buffers[bufferNum][1:] = 0
                ctsb.data_buffers[bufferNum][1:] = 0


            newTimestamps = intTensorToDtList(ctsb.time_buffers[bufferNum][:ctsb.nextidxs[bufferNum][0]])

            # initialize stream parameters if we haven't
            if first:
                first = False    
                frameWidthHeight = (ctsb.data_buffers[bufferNum][0].shape[2], 
                                    ctsb.data_buffers[bufferNum][0].shape[1])
            
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

                cutoffFrameIndex = ctsb.nextidxs[bufferNum][0]
                while firstTimestamp.day < newTimestamps[cutoffFrameIndex-1].day:
                    cutoffFrameIndex -= 1
                cutoffFrameIndex -= 1

                # write and exit the previous days video
                for frame in ctsb.data_buffers[bufferNum][:cutoffFrameIndex]:
                    frame = frame.cpu().numpy()  # Convert from torch tensor to numpy
                    frame = frame.astype(np.uint8)
                    output.write(frame)
                timestamps.extend(newTimestamps[:cutoffFrameIndex])
                timestamps = exitVideo(output, timestamps, tempFilePath)

                # start and write the new day
                timestamps.extend(newTimestamps[cutoffFrameIndex:ctsb.nextidxs[bufferNum][0]])
                tempFilePath = baseFilePath + timestamps[0].strftime('%Y-%m-%d%z') + "/new.mp4"
                output = startNewVideo(timestamps, tempFilePath)
                for frame in ctsb.data_buffers[bufferNum][cutoffFrameIndex:]:
                    frame = frame.cpu().numpy()  # Convert from torch tensor to numpy
                    frame = frame.astype(np.uint8)
                    output.write(frame)
            
            else:
                # else just add to the file
                st = datetime.now()
                for frame in ctsb.data_buffers[bufferNum][:ctsb.nextidxs[bufferNum][0]]:
                    frame = frame.cpu().numpy()  # Convert from torch tensor to numpy
                    frame = frame.astype(np.uint8)
                    output.write(frame)
                timestamps.extend(newTimestamps)
                print(f"have {len(timestamps)} frames in the current video")
                print(f"it took {datetime.now() - st} to write the frames")
                sys.stdout.flush()

                # check if the file is too big and close it if it is
                if len(timestamps) >= 1800:
                    timestamps = exitVideo(output, timestamps, tempFilePath)
                    tryStartNewVideo = True
            
        
        # wait till a round 15 seconds and then
        st = datetime.now()
        secondsToWait = (14 - (st.second % 15)) + (1 - st.microsecond/1_000_000) + 1
        print(f" writer waiting {secondsToWait} till {st + timedelta(seconds=secondsToWait)}")
        time.sleep(secondsToWait)
        
        
        # check if we want to save the last 30, 15 seconds or 1 frame
        last_mr = model_result
        model_result = personSignal[0]
        if model_result and not last_mr:
            print("writing last 30 secs")
            writeCtsbBufferNum((ctsb.lastbn[0] + 2) % 3)
            writeCtsbBufferNum(ctsb.lastbn[0])
        elif model_result or last_mr:
            print("writing last 15 secs")
            writeCtsbBufferNum(ctsb.lastbn[0])

        else:
            print("writing only 30s old frame")
            writeCtsbBufferNum((ctsb.lastbn[0] + 2) % 3, True)
        

        print(f"len of timestamps {len(timestamps)}")
        sys.stdout.flush()

    print("writer worker exiting")
    sys.stdout.flush()
