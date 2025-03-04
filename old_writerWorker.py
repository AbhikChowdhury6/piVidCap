import sys
import cv2
import pandas as pd
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import pickle
import gc

repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")

def dt_to_fnString(dt):
    return dt.astimezone(ZoneInfo("UTC")).strftime('%Y-%m-%dT%H%M%S,%f%z')

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
def writer_worker(child_conn):
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
        child_conn.poll(None)

        from_pipe = pickle.loads(child_conn.recv())  # Get frame from the input
        if from_pipe is None:  # None is the signal to exit
            print("exiting writer worker")
            sys.stdout.flush()
            if len(timestamps) == 0:
                break
            base_file_name = dt_to_fnString(timestamps[0]) + "_" + dt_to_fnString(timestamps[-1])
            
            # close the output and name video
            output.release()
            os.rename(pathToFile + "new.mp4", pathToFile + base_file_name + ".mp4")
            print(f"finished writing the file {base_file_name + '.mp4'}")

            # write the parquet
            tsdf = pd.DataFrame(data=timestamps, columns=['sampleDT'])
            tsdf = tsdf.set_index('sampleDT')
            tsdf.to_parquet(pathToFile + base_file_name + ".parquet.gzip", compression='gzip')
            del tsdf
            output.release()
            break

        newTimestmaps, newFrames =  from_pipe
        if len(newTimestmaps) == 0:
            print("empty list")
            continue

        newTimestmaps = [x.astimezone(ZoneInfo("UTC")) for x in newTimestmaps]
        # print(newTimestmaps)
        #print(f"recived {len(newFrames)} new frames!")
        #print(f"recived {len(newTimestmaps)} new timestamps!")
        sys.stdout.flush()
        
        # if somethig went wrong don't save unaligned data
        if len(newFrames) != len(newTimestmaps):
            print("length of new frames and timestamps don't match ... skipping")
            continue

        if len(timestamps) == 0:
            firstTimestamp = newTimestmaps[0]
        else:
            firstTimestamp = timestamps[0]

        # initialize cap properties
        if first:
            first = False
            frameWidth = int(newFrames[0].shape[1])
            frameHeight = int(newFrames[0].shape[0])

        # start a new output file
        if startNewVideo:
            startNewVideo = False
            pathToFile = "/home/" + user + "/Documents/collectedData/" + \
                deviceName + "_" +firstTimestamp.strftime('%Y-%m-%d%z') + "/"
            os.makedirs(pathToFile, exist_ok=True)
            if os.path.exists(pathToFile + "new.mp4"):
                os.remove(pathToFile + "new.mp4")
            output = cv2.VideoWriter(pathToFile + "new.mp4", 
                        fourcc, 
                        30.0, 
                        (frameWidth, frameHeight))

        # check if the current file crosses midnight
        if firstTimestamp.day < newTimestmaps[-1].day:
            print(f"crossed midnight!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            sys.stdout.flush()
            
            cutoffFrameIndex = len(newFrames)
            while crossesMidnight and firstTimestamp.day < newTimestmaps[cutoffFrameIndex-1].day:
                cutoffFrameIndex -= 1
            cutoffFrameIndex -= 1

            for frame in newFrames[:cutoffFrameIndex]:
                output.write(frame)
            timestamps.extend(newTimestmaps[:cutoffFrameIndex])
        
            base_file_name = dt_to_fnString(timestamps[0]) + "_" + dt_to_fnString(timestamps[-1])
            
            # close the output and name video
            output.release()
            os.rename(pathToFile + "new.mp4", pathToFile + base_file_name + ".mp4")
            print(f"finished writing the file {base_file_name + '.mp4'}")
            sys.stdout.flush()

            # write the parquet
            tsdf = pd.DataFrame(data=timestamps, columns=['sampleDT'])
            tsdf = tsdf.set_index('sampleDT')
            tsdf.to_parquet(pathToFile + base_file_name + ".parquet.gzip", compression='gzip')
            del tsdf
            timestamps = []

            #start a new video and write the cut off part
            startNewVideo = False
            pathToFile = "/home/" + user + "/Documents/collectedData/" + \
                deviceName + "_" + timestamps[cutoffFrameIndex].strftime('%Y-%m-%d%z') + "/"
            os.makedirs(pathToFile, exist_ok=True)
            if os.path.exists(pathToFile + "new.mp4"):
                os.remove(pathToFile + "new.mp4")
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
            gc.collect()
            continue




        # if you're just adding to the existing file
        st = datetime.now()
        for frame in newFrames:
            output.write(frame)
        timestamps.extend(newTimestmaps)
        numAddedFrames += len(newFrames)
        print(f"have {numAddedFrames} frames in the current video")
        print(f"it took {datetime.now() - st} to write the frames")
        sys.stdout.flush()

        # if the file got too big write it
        if numAddedFrames + len(newFrames) >= 1800:
            base_file_name = dt_to_fnString(timestamps[0]) + "_" + dt_to_fnString(timestamps[-1])
            
            # close the output and name video
            output.release()
            startNewVideo = True
            os.rename(pathToFile + "new.mp4", pathToFile + base_file_name + ".mp4")
            print(f"finished writing the file {base_file_name + '.mp4'}")
            sys.stdout.flush()
            # write the parquet
            tsdf = pd.DataFrame(data=timestamps, columns=['sampleDT'])
            tsdf = tsdf.set_index('sampleDT')
            tsdf.to_parquet(pathToFile + base_file_name + ".parquet.gzip", compression='gzip')
            del tsdf
            timestamps = []
            numAddedFrames = 0


    
    print("write worker exiting")
    sys.stdout.flush()



