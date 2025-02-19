import sys
import cv2
import pandas as pd
import os
from datetime import datetime

def getRepoPath():
    cwd = os.getcwd()
    delimiter = "\\" if "\\" in cwd else "/"
    repoPath = delimiter.join(cwd.split(delimiter)[:cwd.split(delimiter).index("piVidCap")]) + delimiter
    return repoPath
repoPath = getRepoPath()
sys.path.append(repoPath + "/piVidCap/")
from deviceInfo import deviceInfo

def dt_to_fnString(dt):
    return dt.tz_convert('UTC').strftime('%Y-%m-%dT%H%M%S,%f%z')

#set these in /etc/enviroment by adding the line DEVICE_NAME="testCam" for example
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
    leftoverFrames = []
    leftoverTimestamps = []
    numAddedFrames = 0
    while True:
        newTimestmaps, newFrames = input_queue.get()  # Get frame from the input 
        timestamps.extend([x.tz_convert('UTC') for x in newTimestmaps])
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

        # initialize output
        if startNewVideo:
            startNewVideo = False
            pathToFile = "/home/" + user + "/Documents/collectedData/" + \
                deviceName + "_" + timestamps[0].strftime('%Y-%m-%d%z') + "/"
            os.makedirs(pathToFile, exist_ok=True)
            output = cv2.VideoWriter(pathToFile + "new.mp4", 
                        fourcc, 
                        30.0, 
                        (frameWidth, frameHeight))

        if timestamps[0].day < timestamps[-1].day:
            crossesMidnight = True
            print(f"crossed midnight!")
            sys.stdout.flush()
        else:
            crossesMidnight = False

        # add any frames and timestamps leftover from the last video cut
        if len(leftoverFrames) != 0:
            newFrames[:0] = leftoverFrames
            newTimestmaps[:0] = leftoverTimestamps
            del leftoverFrames
            del leftoverTimestamps
            leftoverFrames = []
            leftoverTimestamps = []

        # if you're just adding to the existing file
        if not(crossesMidnight or numAddedFrames + len(newFrames) >= 1800):
            for frame in newFrames:
                output.write(frame)
            timestamps.extend(newTimestmaps)
            del newFrames
            del newTimestmaps
            continue

        # if you are finishing a file
        cutoffFrameIndex = 1800
        while crossesMidnight and timestamps[0].day < timestamps[cutoffFrameIndex-1].day:
            cutoffFrameIndex -= 1
        
        leftoverFrames = newFrames[cutoffFrameIndex:].copy()
        leftoverTimestamps = newTimestmaps[cutoffFrameIndex:].copy()

        for frame in newFrames[:cutoffFrameIndex]:
                output.write(frame)
        timestamps.extend(newTimestmaps[:cutoffFrameIndex])
        
        # close the output
        output.release()
        startNewVideo = True
        # calc the base file name
        base_file_name = dt_to_fnString(timestamps[0]) + "_" + dt_to_fnString(timestamps[-1])
        # rename the mp4
        os.rename(pathToFile + "new.mp4", pathToFile + base_file_name + ".mp4")
        # write the parquet
        tsdf = pd.DataFrame(data=timestamps, columns=['sampleDT'])
        tsdf = tsdf.set_index('sampleDT')
        tsdf.to_parquet(pathToFile + base_file_name + ".parquet")

        del newFrames
        del newTimestmaps
        del tsdf



