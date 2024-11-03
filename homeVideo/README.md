for home video processing
- a good start would be to implement yolo v8 and look at the results for the roomCam


There's a couple of TODO's I could get in on 
- code to process the existing data into the new video format with metadata


- for the webcam code I still need to get the saving code to do some stuff
    - keep track of how many frames have been added
        - save every 1.8k frames to a file
        - named the deviceName and timestamp of the start and end frame
    - the only metadata we're generating is the timestamp of every frame and people every 15s
        - ehh even though 1.8k rows is really small might as well keep them in the same format
    - we can save the files locally and sync them using a chron job to a storage/processing server


- how about I just sync the files I need for preocessing over ethernet when I process them
    - the gpu's and not the ethernet should be the bottleneck in the pipeline

one computer with an RTX 3060 should be able to handle running yolo pose on all 5 cameras data
    - yes it will get hot, I'll keep it in the laundry room with the storage server and router, maybe I'll put a box over it to protect it a bit, or use the case in the attic



This is honestly a good goal for the week
TODO:
- write save code for pi's
- flash pi's with code and modify bashrc and the sort
- set up storage and processing server with ubuntu
    - get factorio data off it first
    - install the new ssd
- make chron job for daily transfers
- write code to generate pose data for every frame with a person in it

at that point we'll conseider basic development done for now and get lit with the data as it comes in