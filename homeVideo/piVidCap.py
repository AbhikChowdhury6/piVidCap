from picamera.array import PiRGBArray
from picamera import PiCamera
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


    initalFrameReadStart = datetime.now()
    camera.capture(rawCapture, format="bgr")
    frame = rawCapture.array
    if not ret:
        print("Error: Could not read frame.")

    initalFrameReadEnd = datetime.now()
    print(f"The first Frame took {initalFrameReadEnd - initalFrameReadStart} to capture")

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
    camera.capture(rawCapture, format="bgr")
    frame = rawCapture.array
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
        camera.capture(rawCapture, format="bgr")
        frame = rawCapture.array
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
                    writer_input_queue.put((lrt, lb)) 
                else:
                    writer_input_queue.put((readTimes, mybuffer))
            else:
                # else just save the one frame analyzed for a timelapse
                writer_input_queue.put(([readTimes[0]],[mybuffer[0]]))
            
            delayTill100ms()
            print(f"done with timeperiod starting at {readTimes[0]}")
            lrt = readTimes
            readTimes = [datetime.now(tzlocal.get_localzone())]
            camera.capture(rawCapture, format="bgr")
            frame = rawCapture.array
            lb = mybuffer
            mybuffer = [frame]
            model_input_queue.put(frame)
            lastModelResult = mr

        frameCount += 1