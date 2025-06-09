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

extension = ".mp4"

if os.path.exists(repoPath + "piVidCap/deviceInfo.py"):
    from deviceInfo import deviceInfo, buffSecs
else:
    print("error no deviceInfo found")
    sys.exit()

deviceName = "_".join(deviceInfo.values())
if deviceInfo["instanceName"] == "notSet":
    print("no instance name set")
    sys.stdout.flush()
print(f"device name is {deviceName}")
sys.stdout.flush()

user = os.getenv("USER", "pi")
baseFilePath = "/home/" + user + "/Documents/collectedData/" + \
                deviceName + "_"


def writer_worker(ctsb: CircularTimeSeriesBuffers, personSignal, exitSignal, debugLvl):
    print("in writer worker")
    sys.stdout.flush()
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    frameWidthHeight = (0,0)
    def dt_to_fnString(dt):
        return dt.astimezone(ZoneInfo("UTC")).strftime('%Y-%m-%dT%H%M%S,%f%z')
    
    def exitVideo(output, tsList, tempFilePath):
        if output is None:
            print("output is None")
            return []
        output.release()

        if len(tsList) == 0:
            print('new video empty')
            os.remove(tempFilePath)
            return []

        # rename video
        fbfn = baseFilePath + tsList[0].strftime('%Y-%m-%d%z') + "/"
        fbfn += dt_to_fnString(tsList[0]) + "_" + dt_to_fnString(tsList[-1])
        os.rename(tempFilePath, fbfn + extension)
        
        # write timestamps 
        data = [(ts, i, tsList[0], tsList[-1]) for i, ts in enumerate(tsList)]
        tsdf = pd.DataFrame(data=data, columns=['sampleDT', 'videoIndex', 'videoStartTime', 'videoEndTime'])
        tsdf = tsdf.set_index('sampleDT')
        tsdf.to_parquet(fbfn + ".parquet.gzip", compression='gzip')

        print(f"finished writing the file {fbfn + extension}")
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
    last_mr = False
    last_last_mr = False
    timestamps = []
    first = True
    tryStartNewVideo = True
    output = None
    tempFilePath = None
    leftOverTime = timedelta(seconds=0)
    while True:
        if exitSignal[0] == 1:
            print("writer: got exit signal")
            sys.stdout.flush()
            timestamps = exitVideo(output, timestamps, tempFilePath)
            break

        def writeCtsbBufferNum(bufferNum, onlyFirst=False):
            print(f"writer: using bufferNum {bufferNum}")
            print(f"the current time is: {datetime.now()}")
            print(f"writer: {ctsb.lengths[bufferNum][0]} frames in this buffer")
            nonlocal first
            nonlocal tryStartNewVideo
            nonlocal timestamps
            nonlocal output
            nonlocal tempFilePath
            nonlocal frameWidthHeight
            nonlocal model_result
            nonlocal last_mr
            nonlocal last_last_mr

            if ctsb.lengths[bufferNum][0] == 0:
                return
            
            if onlyFirst:
                ctsb.lengths[bufferNum][0] = 1


            newTimestamps = intTensorToDtList(ctsb.time_buffers[bufferNum][:ctsb.lengths[bufferNum][0]])
            #print(f"len of new timestamps is {len(newTimestamps)}")
            #print("the first timestamps are" + " ".join([t.strftime("%S.%f") for t in newTimestamps[:20]]))
            #print("the last timestamps are " + " ".join([t.strftime("%S.%f") for t in newTimestamps[-20:]]))
            print(f"the first timestamp is {newTimestamps[0]}")
            print(f"the last timestamp is {newTimestamps[-1]}")



            # initialize stream parameters if we haven't
            if first:
                first = False    
                frameWidthHeight = (ctsb.data_buffers[bufferNum][0].shape[1], 
                                    ctsb.data_buffers[bufferNum][0].shape[0])
                print(f"writer: setting frameWidthHeight to {frameWidthHeight}")
            
            # check if we have to make a new file
            if tryStartNewVideo:
                tryStartNewVideo = False
                tempFilePath = baseFilePath + newTimestamps[0].strftime('%Y-%m-%d%z') + "/new" + extension
                output = startNewVideo(tempFilePath)

            # if crosses midnight close the file and start a new one
            if len(timestamps) == 0:
                firstTimestamp = newTimestamps[0]
            else:
                firstTimestamp = timestamps[0]
            
            if firstTimestamp.day == newTimestamps[-1].day:
                # else just add to the file
                # st = datetime.now()
                    
                for frame in ctsb.data_buffers[bufferNum][:ctsb.lengths[bufferNum][0]]:
                    frame = frame.cpu().numpy()  # Convert from torch tensor to numpy
                    frame = frame.astype(np.uint8)
                    success = output.write(frame)

                timestamps.extend(newTimestamps)
                #print(f"writer: have {len(timestamps)} frames in the current video")
                #print(f"writer: it took {datetime.now() - st} to write the frames")
                sys.stdout.flush()

                # check if the file is too big and close it if it is
                if len(timestamps) >= 1800:
                    timestamps = exitVideo(output, timestamps, tempFilePath)
                    tryStartNewVideo = True
                return
            
        
            print(f"writer: crossed midnight!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            sys.stdout.flush()

            timestamps = exitVideo(output, timestamps, tempFilePath)
            timestamps.extend(newTimestamps)
            tempFilePath = baseFilePath + timestamps[0].strftime('%Y-%m-%d%z') + "/new" + extension
            output = startNewVideo(tempFilePath)
            for frame in ctsb.data_buffers[bufferNum][:ctsb.lengths[bufferNum][0]]:
                    frame = frame.cpu().numpy()  # Convert from torch tensor to numpy
                    frame = frame.astype(np.uint8)
                    success = output.write(frame)



        print()

        # wait if the last write took less than buffSecs secs
        if first:
            writeStartTime = datetime.now()

        runTime = datetime.now() - writeStartTime
        if runTime + leftOverTime < timedelta(seconds=buffSecs):
            leftOverTime = timedelta(seconds=0)
            # wait till a about round buffSecs seconds and then
            st = datetime.now()
            secondsToWait = ((buffSecs-1) - (st.second % buffSecs)) + (1 - st.microsecond/1_000_000) + .2
            print(f"writer: waiting {secondsToWait} till {st + timedelta(seconds=secondsToWait)}")
            time.sleep(secondsToWait)
        else:
            print(f"it took longer than {buffSecs}s to write, not waiting")
            leftOverTime = (runTime + leftOverTime) - timedelta(seconds=buffSecs)
            print(f"{leftOverTime} behind")
        
        
        writeStartTime = datetime.now()
        # check if we want to save the last 2buffSecs, 1buffSecs or 1 frame
        last_last_mr = last_mr
        last_mr = model_result
        model_result = personSignal[0].clone()
        print(f"writer: model result is {model_result}")
        # print(f"writer: last_mr is {last_mr}")
        if model_result and not last_mr:
            print(f"writer: writing last {2*buffSecs} secs")
            writeCtsbBufferNum((ctsb.bn[0] + 1) % 3)
            writeCtsbBufferNum((ctsb.bn[0] + 2) % 3)
        elif model_result or last_mr:
            print(f"writer: writing last {buffSecs} secs")
            writeCtsbBufferNum((ctsb.bn[0] + 2) % 3)

        elif not last_last_mr:
            print(f"writer: writing only {2*buffSecs}s old frame")
            writeCtsbBufferNum((ctsb.bn[0] + 1) % 3, True)
        else:
            print(f"dont even need to wrtie {2*buffSecs}s old frame since we already did")
        

        print(f"writer: have {len(timestamps)} frames in the current video")
        print(f"writer: it took {datetime.now() - writeStartTime} to write the frames")
        sys.stdout.flush()

    print("writer: writer worker exiting")
    sys.stdout.flush()
