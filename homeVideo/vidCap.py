import cv2
from datetime import datetime
import time
import tzlocal
import pandas as pd
import signal
import sys

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
    cap = cv2.VideoCapture(1)
    timeAfterCapDefined = datetime.now() 

    # Check if the webcam is opened correctly
    if not cap.isOpened():
        print("Error: Could not open video.")
        exit()

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    print(f"The cap took {timeAfterCapDefined - timeBeforeCapDefined} to initialize")

    initalFrameReadStart = datetime.now()
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame.")

    initalFrameReadEnd = datetime.now()
    print(f"The first Frame took {initalFrameReadEnd - initalFrameReadStart} to capture")
    # ret, frame = cap.read()


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
    result = model_output_queue.get()
    modelEndTime = datetime.now()

    print(f"the model took {modelEndTime - modelStartTime} to setup and run")
    print("Model output:", result)

    modelStartTime = datetime.now()
    model_input_queue.put(frame)
    result = model_output_queue.get()
    modelEndTime = datetime.now()

    print(f"the model took {modelEndTime - modelStartTime} to run")
    print("Model output:", result)


    writer_input_queue = mp.Queue()
    writer_output_queue = mp.Queue()

    writer_process = mp.Process(target=writer_worker, args=(writer_input_queue, writer_output_queue))
    writer_process.start()

    # actual capture code
    frameCount = 0

    # wait till a round 15 seconds
    currTime = datetime.now()
    time.sleep((14 - (currTime.second % 15)) + (1 - currTime.microsecond/1_000_000))

    readTimes = [datetime.now(tzlocal.get_localzone())]
    ret, frame = cap.read()
    mybuffer = [frame]
    model_input_queue.put(frame)

    def modelResult():
        if model_output_queue.empty(): print("waiting for processing")
        return model_output_queue.get()

    def delayTill100ms(): # a bit offset to compensate for read lag
        msToDelay = 100 - ((datetime.now().microsecond / 1000) % 100)
        time.sleep(msToDelay/1000)

    lastModelResult = True
    while True:
        delayTill100ms()
        
        #logging and frame cap
        readTimes.append(datetime.now(tzlocal.get_localzone()))
        ret, frame = cap.read()
        mybuffer.append(frame)

        if (datetime.now().second + 1) % 15 == 0 and datetime.now().microsecond > 900_000:
            # if there was people then save the last 15 seconds
            mr = modelResult()
            if mr:
                if not lastModelResult:
                    writer_input_queue.put((lrt.extend(readTimes), lb.extend(mybuffer))) 
                else:
                    writer_input_queue.put((readTimes, mybuffer))
            else:
                # else just save the one frame analyzed for a timelapse
                writer_input_queue.put((readTimes,[mybuffer[0]]))
            
            delayTill100ms()
            print(readTimes[0])
            lrt = readTimes
            readTimes = [datetime.now(tzlocal.get_localzone())]
            ret, frame = cap.read()
            lb = mybuffer
            mybuffer = [frame]
            model_input_queue.put(frame)
            lastModelResult = mr

        frameCount += 1