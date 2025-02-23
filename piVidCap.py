from picamera2 import Picamera2
import cv2
from datetime import datetime
import time
import pandas as pd
import signal
import sys
import os

repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")

import torch.multiprocessing as mp
from modelWorker import model_worker
from writerWorker import writer_worker


if __name__ == "__main__":
    #the spawend processes will build up unless exited
    def handle_sigint(signal_received, frame):
        print("SIGINT received. Exiting gracefully...")
        model_input_queue.put(None)
        writer_input_queue.put(None)
        sys.exit(130)  # Exit code 130 is commonly used for SIGINT
    # Set up the signal handler for SIGINT
    signal.signal(signal.SIGINT, handle_sigint)
    
    timeBeforeCapDefined = datetime.now() 
    picam2 = Picamera2()
    video_config = picam2.create_video_configuration(main={"size": (1920, 1080), "format": "RGB888"})
    picam2.configure(video_config)
    picam2.start()
    timeAfterCapDefined = datetime.now() 
    print(f"The cap took {timeAfterCapDefined - timeBeforeCapDefined} to initialize")
    del timeAfterCapDefined
    del timeBeforeCapDefined


    def getFrame():
        # -1 for no rotation +1 per 90 degrees clockwize turn
        if int(sys.argv[1]) == -1:
            return picam2.capture_array()
        else:
            return cv2.rotate(picam2.capture_array(), int(sys.argv[1]))



    initalFrameReadStart = datetime.now()
    frame = getFrame()

    initalFrameReadEnd = datetime.now()
    print(f"The first Frame took {initalFrameReadEnd - initalFrameReadStart} to capture")
    del initalFrameReadEnd
    del initalFrameReadStart


    mp.set_start_method('spawn', force=True)
    mp.freeze_support()

    model_input_queue = mp.Queue()
    model_output_queue = mp.Queue()

    # Start the worker process
    model_process = mp.Process(target=model_worker, args=(model_input_queue, model_output_queue))
    model_process.start()

    print(f"is the model process alive?: {model_process.is_alive()}")
    modelStartTime = datetime.now()
    model_input_queue.put(frame)
    print(" going to wait for model")
    start_time = time.time()
    while model_output_queue.empty(): 
        if time.time() - start_time > 20:
            print("took more than 20 seconds to run exiting")
            sys.exit()
        time.sleep(1)
    modelEndTime = datetime.now()
    print(f"the model took {modelEndTime - modelStartTime} to setup and run")
    print("Model output:", mr)


    writer_input_queue = mp.Queue()
    writer_output_queue = mp.Queue()

    writer_process = mp.Process(target=writer_worker, args=(writer_input_queue, writer_output_queue))
    writer_process.start()

    # actual capture code
    def modelResult():
        if model_output_queue.empty(): print("waiting for processing")
        return model_output_queue.get()

    def delayTill100ms(): # a bit offset to compensate for read lag
        msToDelay = 100 - ((datetime.now().microsecond / 1000) % 100)
        time.sleep(msToDelay/1000)

    def health_checks():
        print(f"is model alive?: {model_process.is_alive()}")
        print(f"is writer alive?: {writer_process.is_alive()}")
        print()
        if not (model_process.is_alive() and writer_process.is_alive()):
            print("one of the processes died exiting everything")
            model_input_queue.put(None)
            writer_input_queue.put(None)
            return False
        return True

    

    myFrameBuffer = []
    myTimesBuffer = []
    mr = False
    while True:
        frame = getFrame()
        frameTime = datetime.now().astimezone()

        myFrameBuffer.append(frame)
        myTimesBuffer.append(frameTime)

        # if not a round 15 seconds
        if ((not ((datetime.now().second + 1) % 15 == 0 
                and datetime.now().microsecond > 900_000))
            and len(myTimesBuffer) <= 151):
            delayTill100ms()
            continue

        #it's on a 15th seconds or the buffer is too big
        st = datetime.now()
        if not health_checks():
            break
        print(f"it took {datetime.now() - st} for health_checks")

        st = datetime.now()
        model_input_queue.put(myFrameBuffer[-1])
        print(f"it took {datetime.now() - st} for putting in the model input queue")

        maxTime = max(b - a for a, b in zip(timestamps, timestamps[1:]))
        print(f"the max frame interval was {maxTime}")
        print(f"got {len(myTimesBuffer)} frames the past 15 seconds")
        print(f"it is {datetime.now()}")
        last_mr = mr

        st = datetime.now()
        mr = modelResult()
        print(f"it took {datetime.now() - st} to get the model result")
        
        st = datetime.now()
        if mr: print("saw someone!!!")
        if mr or last_mr:
            print("sending whole buffer")
            writer_input_queue.put((myTimesBuffer, myFrameBuffer))
        else:
            print("only sending most recent frame")
            writer_input_queue.put(([myTimesBuffer[-1]], [myFrameBuffer[-1]]))
        print(f"it took {datetime.now() - st} for putting in the write input queue")

        myFrameBuffer = []
        myTimesBuffer = []

        delayTill100ms()