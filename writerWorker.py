import sys
import cv2
import pandas as pd
import os
from datetime import datetime
from zoneinfo import ZoneInfo


repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")

def dt_to_fnString(dt):
    return dt.tz_convert('UTC').strftime('%Y-%m-%dT%H%M%S,%f%z')

if os.path.exists(repoPath + "piVidCap/deviceInfo.py"):
    from deviceInfo import deviceInfo
else:
    from collections import OrderedDict
    keys = ["responsiblePartyName", "instanceName", "developingPartyName", "deviceName", "dataType", "dataSource"]
    values = ["abhik", "notSet", "abhik", "unknown", "mp4", "piVidCap"]
    deviceInfo = OrderedDict(zip(keys, values))

deviceName = "_".join(deviceInfo.keys())
if deviceInfo["instanceName"] == "notSet":
    print("no instance name set")
    sys.stdout.flush()

user = os.getenv("USER", "pi")
sys.stdout.flush()
# what do we need to do
    # keep track of how many frames there are and save a video every 1.8k frames  
    # save to a folder called deviceName-date in a folder called collectedData


# the chron job can come in and send off that folder to 
# /home/{remoteUsername}/Documents/videoData/{year-month}/ in the storage and processing server
# open chrontab for editing with chrontab -e
# run the script at 3 am ngl I'm pretty sure everyone in the house will be pretty asleep and they wont mind the bandwith usage
# add the line
# 0 3 * * * /home/pi/Documents/videoProcessing/send.sh


# Define the codec and create a VideoWriter object
def writer_worker(input_queue, output_queue):
    print("in writer worker")
    sys.stdout.flush()
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    timestamps = []
    frameWidth = 0
    frameHeight = 0
    first = True
    startNewVideo = True
    numAddedFrames = 0
    while True:
        newTimestmaps, newFrames = input_queue.get()  # Get frame from the input 
        timestamps.extend([x.astimezone(ZoneInfo("UTC")) for x in newTimestmaps])
        # print(newTimestmaps)
        print(f"recived {len(newFrames)} new frames!")
        print(f"recived {len(newTimestmaps)} new timestamps!")
        sys.stdout.flush()

        if newFrames is None:  # None is the signal to exit
            print("exiting writer worker")
            sys.stdout.flush()
            output.release()
            break
        
        # if somethig went wrong don't save unaligned data
        if len(newFrames) != len(newTimestmaps):
            continue

        # initialize cap properties
        if first:
            first = False
            frameWidth = int(newFrames[0].shape[1])
            frameHeight = int(newFrames[0].shape[0])

        # start a new output file
        if startNewVideo:
            startNewVideo = False
            pathToFile = "/home/" + user + "/Documents/collectedData/" + \
                deviceName + "_" + timestamps[0].strftime('%Y-%m-%d%z') + "/"
            os.makedirs(pathToFile, exist_ok=True)
            output = cv2.VideoWriter(pathToFile + "new.mp4", 
                        fourcc, 
                        30.0, 
                        (frameWidth, frameHeight))

        # check if the current file crosses midnight
        if timestamps[0].day < timestamps[-1].day:
            crossesMidnight = True
            print(f"crossed midnight!")
            sys.stdout.flush()
        else:
            crossesMidnight = False


        # if you're just adding to the existing file
        if not(crossesMidnight or numAddedFrames + len(newFrames) >= 1800):
            for frame in newFrames:
                output.write(frame)
            timestamps.extend(newTimestmaps)
            numAddedFrames += len(newFrames)
            print(f"have {numAddedFrames} frames in the current video")

        # if the file just got too big
        elif not crossesMidnight and numAddedFrames + len(newFrames) >= 1800:
            if numAddedFrames + len(newFrames) >= 1800:
                for frame in newFrames:
                    output.write(frame)
            timestamps.extend(newTimestmaps)
            
            base_file_name = dt_to_fnString(timestamps[0]) + "_" + dt_to_fnString(timestamps[-1])
            
            # close the output and name video
            output.release()
            startNewVideo = True
            os.rename(pathToFile + "new.mp4", pathToFile + base_file_name + ".mp4")
            # write the parquet
            tsdf = pd.DataFrame(data=timestamps, columns=['sampleDT'])
            tsdf = tsdf.set_index('sampleDT')
            tsdf.to_parquet(pathToFile + base_file_name + ".parquet.gzip", compression='gzip')
            del tsdf

            numAddedFrames = 0

            
        # if the file crosses midnight
        else:
            cutoffFrameIndex = len(newFrames)
            while crossesMidnight and timestamps[0].day < timestamps[cutoffFrameIndex-1].day:
                cutoffFrameIndex -= 1
        

            for frame in newFrames[:cutoffFrameIndex]:
                output.write(frame)
            timestamps.extend(newTimestmaps[:cutoffFrameIndex])
        
            base_file_name = dt_to_fnString(timestamps[0]) + "_" + dt_to_fnString(timestamps[-1])
            
            # close the output and name video
            output.release()
            os.rename(pathToFile + "new.mp4", pathToFile + base_file_name + ".mp4")
            # write the parquet
            tsdf = pd.DataFrame(data=timestamps, columns=['sampleDT'])
            tsdf = tsdf.set_index('sampleDT')
            tsdf.to_parquet(pathToFile + base_file_name + ".parquet.gzip", compression='gzip')
            del tsdf

            #start a new video and write the cut off part
            startNewVideo = False
            pathToFile = "/home/" + user + "/Documents/collectedData/" + \
                deviceName + "_" + timestamps[0].strftime('%Y-%m-%d%z') + "/"
            os.makedirs(pathToFile, exist_ok=True)
            output = cv2.VideoWriter(pathToFile + "new.mp4", 
                        fourcc, 
                        30.0, 
                        (frameWidth, frameHeight))


            for frame in newFrames[cutoffFrameIndex:]:
                output.write(frame)
            timestamps = newTimestmaps[cutoffFrameIndex:]
            numAddedFrames = len(timestamps)
        
        del newFrames
        del newTimestmaps



