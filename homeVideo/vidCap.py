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
    cap = cv2.VideoCapture(sys.argv[1])
    timeAfterCapDefined = datetime.now() 

    # Check if the webcam is opened correctly
    if not cap.isOpened():
        print("Error: Could not open video.")
        exit()

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    print(f"The cap took {timeAfterCapDefined - timeBeforeCapDefined} to initialize")
    del timeAfterCapDefined
    del timeBeforeCapDefined

    initalFrameReadStart = datetime.now()
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame.")

    initalFrameReadEnd = datetime.now()
    print(f"The first Frame took {initalFrameReadEnd - initalFrameReadStart} to capture")
    del initalFrameReadEnd
    del initalFrameReadStart
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
    del modelEndTime
    del modelStartTime


    writer_input_queue = mp.Queue()
    writer_output_queue = mp.Queue()

    writer_process = mp.Process(target=writer_worker, args=(writer_input_queue, writer_output_queue))
    writer_process.start()

    # actual capture code

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
        del ret
        del frame
        ret, frame = cap.read()
        mybuffer.append(frame)

        if (datetime.now().second + 1) % 15 == 0 and datetime.now().microsecond > 900_000:
            # if there was people then save the last 15 seconds
            mr = modelResult()
            if mr:
                print("saw someone!")
                if not lastModelResult:
                    lrt.extend(readTimes)
                    lb.extend(mybuffer)
                    # print(lrt)
                    # print(len(lb))
                    print(f"sending {len(lrt)} frames")
                    writer_input_queue.put((lrt, lb)) 
                else:
                    print(f"sending {len(readTimes)} frames")
                    writer_input_queue.put((readTimes, mybuffer))
            else:
                # else just save the one frame analyzed for a timelapse
                print("sending 1 frame")
                writer_input_queue.put(([readTimes[0]],[mybuffer[0]]))
            
            delayTill100ms()
            print(f"done with timeperiod starting at {readTimes[0]}")
            lrt = []
            lrt.clear()
            lrt = readTimes
            readTimes.clear()
            readTimes = [datetime.now(tzlocal.get_localzone())]
            del frame
            del ret
            ret, frame = cap.read()
            lb = []
            lb.clear()
            lb = mybuffer
            mybuffer.clear()
            mybuffer = [frame]
            model_input_queue.put(frame)
            lastModelResult = mr
            print(f"is model alive?: {model_process.is_alive()}")
            print(f"is writer alive?: {writer_process.is_alive()}")
            print()
            if not (model_process.is_alive() and writer_process.is_alive()):
                print("one of the processes died exiting everything")
                model_input_queue.put(None)
                writer_input_queue.put(None)
                break



