import sys
import cv2
import pandas as pd
import os

#set these in /etc/enviroment by adding the line DEVICE_NAME="testCam" for example
deviceName = os.getenv("DEVICE_NAME", "notSet")
if deviceName == "notSet":
    print("no device name set")

# what do we need to do
    # keep track of how many frames there are and save a video every 1.8k frames  
    # save to a folder called deviceName-date in a folder called collectedData


# the chron job can come in and send off that folder to 
# /home/{remoteUsername}/Documents/videoData/{year-month}/ in the storage and processing server

# Define the codec and create a VideoWriter object
def writer_worker(input_queue, output_queue):
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    timestamps = []
    frames = []
    frameWidth = 0
    frameHeight = 0
    first = True
    while True:
        newTimestmaps, newFrames = input_queue.get()  # Get frame from the input queue
        
        if newFrames is None:  # None is the signal to exit
            output.release()
            break
        
        if first:
            first = False
            frameWidth = int(newFrames[0].shape[1])
            frameHeight = int(newFrames[0].shape[0])
            lastVideoDay = newTimestmaps[0].day
            

        frames.extend(newFrames)
        timestamps.extend(newTimestmaps)

        if frames[0].day < frames[-1].day:
            crossesMidnight = True
        else:
            crossesMidnight = False

        if len(frames) >= 1800 or crossesMidnight:
 
            if crossesMidnight:
                endIndex = len(frames)
                while frames[0].day < frames[endIndex].day:
                    endIndex -= 1
            else:
                endIndex = 1800
            
            pathToFile = "/home/pi/Documents/collectedData/" + \
                        deviceName + "_" + timestamps[0].strftime('%Y-%m-%d') + "/"
            os.makedirs(pathToFile, exist_ok=True)

            fileName = deviceName + "_" + \
                        timestamps[0].strftime('%Y-%m-%dT%H%M%S%z') + "_" + \
                        timestamps[endIndex-1].strftime('%Y-%m-%dT%H%M%S%z')

            #save frames to a video
            output = cv2.VideoWriter(pathToFile + fileName + ".mp4", 
                                    fourcc, 
                                    30.0, 
                                    (frameWidth, frameHeight))
            for frame in frames[:endIndex]:
                output.write(frame)
            output.release()
            frames = frames[endIndex:]

            # also save timestamps
            tsdf = pd.DataFrame(data=timestamps[:endIndex], columns=['sampleDT'])
            tsdf.to_parquet(pathToFile + fileName + ".parquet")
            timestamps = timestamps[endIndex:]


        
