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

        if not(crossesMidnight or numAddedFrames + len(newFrames) >= 1800):
            for frame in newFrames:
                output.write(frame)
            timestamps.extend(newTimestmaps)
            del newFrames
            del newTimestmaps
            continue

        cutoffFrameIndex = 1800
        while crossesMidnight and timestamps[0].day < timestamps[cutoffFrameIndex-1].day:
            cutoffFrameIndex -= 1
        
        nextFrames = newFrames[cutoffFrameIndex:]
        nextTimestamps = newTimestmaps[cutoffFrameIndex:]

        for frame in newFrames[:cutoffFrameIndex]:
                output.write(frame)
        timestamps.extend(newTimestmaps[:cutoffFrameIndex])
        
        # close the output
        output.release()
        # calc the base file name
        base_file_name = dt_to_fnString(timestamps[0]) + "_" + dt_to_fnString(timestamps[-1])

        # rename the mp4
        os.rename(pathToFile + "new.mp4", pathToFile + base_file_name + ".mp4")
        # write the parquet
        

        
        
        # if it does cross midnight or is
        # find the last frame before midnight or the cutoff
        # save all of those frames to the curent file
        # release the output
        # name the file it's final name

        # create a new folder for the new day and a new file
        # write the rest of the frames to a new file

        #if it doesn't cross midnight then or is above the target length continue

        # nahhhhh first check if there is a midnight split needed

        # add the new frames
        for frame in newFrames:
            output.write(frame)
        numAddedFrames += len(newFrames)
        print(f"have {len(numAddedFrames)} total frames in this file!")
        del newFrames
        # add the new timestamps




        

        # here add the relevant number of new frames to the output
        # and to do that we have to check if midnight has passed and how many frames we've already written
        if crossesMidnight

        timestamps.extend(newTimestmaps)
        del newFrames
        del newTimestmaps
        
        print(f"have {len(timestamps)} total timestamps!")
        sys.stdout.flush()

        

        if frame >= 1800 or crossesMidnight:

            if crossesMidnight:
                endIndex = len(timestamps)-1
                while timestamps[0].tz_convert("UTC").day < timestamps[endIndex-1].tz_convert("UTC").day:
                    endIndex -= 1
            else:
                endIndex = 1800
            
            print(f"attempting to write {endIndex} frames")
            sys.stdout.flush()

            
            fileName = deviceName + "_" + \
                        timestamps[0].strftime('%Y-%m-%dT%H%M%S,%f%z') + "_" + \
                        timestamps[endIndex-1].strftime('%Y-%m-%dT%H%M%S,%f%z')

            print(f"wrote {endIndex} frames to the name " + fileName)
            sys.stdout.flush()


            #save frames to a video
            writeStartTime = datetime.now()
            for frame in frames[:endIndex]:
                output.write(frame)
            output.release()
            print(f"writing took {datetime.now() - writeStartTime}")
            sys.stdout.flush()
            del writeStartTime

            leftoverFrames = frames[endIndex:]
            del frames
            frames = leftoverFrames
            del leftoverFrames
            print(f"{len(frames)} is the number of frames left")
            sys.stdout.flush()

            # also save timestamps
            tsdf = pd.DataFrame(data=timestamps[:endIndex], columns=['sampleDT'])
            tsdf = tsdf.set_index('sampleDT')
            tsdf.to_parquet(pathToFile + fileName + ".parquet")
            leftoverTimestamps = timestamps[endIndex:]
            del timestamps
            timestamps = leftoverTimestamps
            del leftoverTimestamps
            # sys.stdout.flush()


        
