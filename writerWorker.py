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
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
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

        print(f"finished writing the file {fbfn}.mp4")
        return []

    def startNewVideo(tempFilePath):
        os.makedirs(tempFilePath[:-7], exist_ok=True)
        if os.path.exists(tempFilePath):
                os.remove(tempFilePath)
        
        print("starting a new output")
        print(tempFilePath)
        print(f"writer: frameWidthHeight: {frameWidthHeight}")
        print(f"writer: fourcc: {fourcc}")
        output = cv2.VideoWriter(tempFilePath, 
                        fourcc, 
                        30.0, 
                        frameWidthHeight)
        if not output.isOpened():
            print(f"writer: Failed to open video writer")
            return None
        
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
            print("writer: got exit signal")
            sys.stdout.flush()
            timestamps = exitVideo(output, timestamps, tempFilePath)
            break

        def writeCtsbBufferNum(bufferNum, onlyFirst=False):
            print(f"writer: using bufferNum {bufferNum}")
            print(f"writer: going to try to write {ctsb.lengths[bufferNum][0]} frames")
            nonlocal first
            nonlocal tryStartNewVideo
            nonlocal timestamps
            nonlocal output
            nonlocal tempFilePath
            nonlocal frameWidthHeight

            if ctsb.lengths[bufferNum][0] == 0:
                return
            
            if onlyFirst:
                ctsb.lengths[bufferNum][0] = 1


            newTimestamps = intTensorToDtList(ctsb.time_buffers[bufferNum][:ctsb.lengths[bufferNum][0]])

            # initialize stream parameters if we haven't
            if first:
                first = False    
                frameWidthHeight = (ctsb.data_buffers[bufferNum][0].shape[1], 
                                    ctsb.data_buffers[bufferNum][0].shape[0])
                print(f"writer: setting frameWidthHeight to {frameWidthHeight}")
            
            # check if we have to make a new file
            if tryStartNewVideo:
                tryStartNewVideo = False
                tempFilePath = baseFilePath + newTimestamps[0].strftime('%Y-%m-%d%z') + "/new.mp4"
                output = startNewVideo(tempFilePath)

            # if crosses midnight close the file and start a new one
            if len(timestamps) == 0:
                firstTimestamp = newTimestamps[0]
            else:
                firstTimestamp = timestamps[0]
            
            if firstTimestamp.day < newTimestamps[-1].day:
                print(f"writer: crossed midnight!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                sys.stdout.flush()

                cutoffFrameIndex = ctsb.lengths[bufferNum][0]
                while firstTimestamp.day < newTimestamps[cutoffFrameIndex-1].day:
                    cutoffFrameIndex -= 1
                cutoffFrameIndex -= 1

                # write and exit the previous days video
                for frame in ctsb.data_buffers[bufferNum][:cutoffFrameIndex]:
                    frame = frame.cpu().numpy()  # Convert from torch tensor to numpy
                    frame = frame.astype(np.uint8)
                    frame = np.transpose(frame, (1, 0, 2))
                    frame = np.ascontiguousarray(frame)
                    print(f"writer: frame type: {type(frame)}")
                    success = output.write(frame)
                    if not success:
                        print(f"writer: Failed to write frame")
                timestamps.extend(newTimestamps[:cutoffFrameIndex])
                timestamps = exitVideo(output, timestamps, tempFilePath)

                # start and write the new day
                timestamps.extend(newTimestamps[cutoffFrameIndex:ctsb.lengths[bufferNum][0]])
                tempFilePath = baseFilePath + timestamps[0].strftime('%Y-%m-%d%z') + "/new.mp4"
                output = startNewVideo(tempFilePath)
                for frame in ctsb.data_buffers[bufferNum][cutoffFrameIndex:]:
                    frame = frame.cpu().numpy()  # Convert from torch tensor to numpy
                    frame = frame.astype(np.uint8)
                    frame = np.transpose(frame, (1, 0, 2))
                    frame = np.ascontiguousarray(frame)
                    print(f"writer: frame type: {type(frame)}")
                    success = output.write(frame)
                    if not success:
                        print(f"writer: Failed to write frame")
            
            else:
                # else just add to the file
                st = datetime.now()
                #if output.isOpened():
                #    print(f"writer: output is opened")
                    
                for frame in ctsb.data_buffers[bufferNum][:ctsb.lengths[bufferNum][0]]:
                    frame = frame.cpu().numpy()  # Convert from torch tensor to numpy
                    frame = frame.astype(np.uint8)
                    #frame = np.transpose(frame, (1, 0, 2))
                    frame = np.ascontiguousarray(frame)
                    #testFrame  = np.random.randint(0, 50, (1080, 1920, 3), dtype=np.uint8)
                    #success = output.write(testFrame)
                    #if not success:
                    #     print(f"writer: Failed to write test frame")
                    # else:
                    #     print(f"writer: wrote test frame")
                    #print(f"writer: frame dtype: {frame.dtype}")
                    #print(f"writer: frame type: {type(frame)}")
                    #print(f"writer: frame min: {frame.min()}, max: {frame.max()}")
                    #print(f"writer: frame shape: {frame.shape}")
                    #frame = cv2.resize(frame, (1920, 1080))
                    #print(f"writer: frame shape after resize: {frame.shape}")
                    success = output.write(frame)
                    if not success:
                        print(f"writer: Failed to write cap frame frame")
                    else:
                        print(f"writer: wrote cap frame frame")
                timestamps.extend(newTimestamps)
                print(f"writer: have {len(timestamps)} frames in the current video")
                print(f"writer: it took {datetime.now() - st} to write the frames")
                sys.stdout.flush()

                # check if the file is too big and close it if it is
                if len(timestamps) >= 1800:
                    timestamps = exitVideo(output, timestamps, tempFilePath)
                    tryStartNewVideo = True
            
        
        # wait till a round 15 seconds and then
        st = datetime.now()
        secondsToWait = (14 - (st.second % 15)) + (1 - st.microsecond/1_000_000) + 1
        print(f"writer: waiting {secondsToWait} till {st + timedelta(seconds=secondsToWait)}")
        time.sleep(secondsToWait)
        
        
        # check if we want to save the last 30, 15 seconds or 1 frame
        last_mr = model_result
        model_result = personSignal[0].clone()
        print(f"writer: model result is {model_result}")
        print(f"writer: last_mr is {last_mr}")
        if model_result and not last_mr:
            print("writer: writing last 30 secs")
            writeCtsbBufferNum((ctsb.bn[0] + 1) % 3)
            writeCtsbBufferNum((ctsb.bn[0] + 2) % 3)
        elif model_result or last_mr:
            print("writer: writing last 15 secs")
            writeCtsbBufferNum((ctsb.bn[0] + 2) % 3)

        else:
            print("writer: writing only 30s old frame")
            writeCtsbBufferNum((ctsb.bn[0] + 1) % 3, True)
        

        print(f"writer: len of timestamps {len(timestamps)}")
        sys.stdout.flush()

    print("writer: writer worker exiting")
    sys.stdout.flush()
