from picamera2 import Picamera2
import cv2
import numpy as np
from datetime import datetime, timedelta
import time
import select
import pandas as pd
import signal
import sys
import os

repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")

import torch.multiprocessing as mp
from modelWorker import model_worker
from writerWorker import writer_worker
from deviceInfo import subSample

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
            frame = picam2.capture_array()
        else:
            frame =  cv2.rotate(picam2.capture_array(), int(sys.argv[1]))
        
        if subSample == 1:
            return frame
        return np.ascontiguousarray(frame[::subSample, ::subSample, :])



    initalFrameReadStart = datetime.now()
    frame = getFrame()

    initalFrameReadEnd = datetime.now()
    print(f"The first Frame took {initalFrameReadEnd - initalFrameReadStart} to capture")
    del initalFrameReadEnd
    del initalFrameReadStart


    mp.set_start_method('spawn', force=True)
    mp.freeze_support()

    model_parent_conn, model_child_conn = mp.Pipe()

    # Start the worker process
    model_process = mp.Process(target=model_worker, args=(child_conn, ))
    model_process.start()

    print(f"is the model process alive?: {model_process.is_alive()}")
    modelStartTime = datetime.now()
    model_parent_conn.send(pickle.dumps(frame))
    print("going to wait for model")
    if not model_parent_conn.poll(20):
        print("took more than 20 seconds to run, exiting")
        sys.exit()
    modelEndTime = datetime.now()
    print(f"the model took {modelEndTime - modelStartTime} to setup and run")


    writer_parent_conn, writer_child_conn = mp.Pipe()

    writer_process = mp.Process(target=writer_worker, args=(writer_parent_conn, ))
    writer_process.start()

    # actual capture code
    def modelResult():
        if model_parent_conn.poll(0.01): 
            return pickle.loads(model_parent_conn.recv())

        print("waiting for processing")
        if child_conn.poll():
            return pickle.loads(model_parent_conn.recv())


    def delayTill100ms(): # a bit offset to compensate for read lag
        msToDelay = 100 - ((datetime.now().microsecond / 1000) % 100)
        time.sleep(msToDelay/1000)

    def health_checks():
        if not (model_process.is_alive() and writer_process.is_alive()):
            print(f"is model alive?: {model_process.is_alive()}")
            print(f"is writer alive?: {writer_process.is_alive()}")
            print("one of the processes died exiting everything")
            model_parent_conn.send(None)
            writer_parent_conn.send(None)
            return False
        return True

    def printTimeStats(myTimesBuffer):
        maxTime = max(b - a for a, b in zip(myTimesBuffer, myTimesBuffer[1:]))
        print(f"the max frame interval was {maxTime}")
        print(f"got {len(myTimesBuffer)} frames the past 15 seconds")

    

    myFrameBuffer = []
    myTimesBuffer = []
    minus30Frames = []
    minus30Times = []
    most_recent_write_time = pd.Timestamp.min.tz_localize("UTC")
    mr = False
    while True:
        frame = getFrame()
        frameTime = datetime.now().astimezone()

        frameTS = datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")
        cv2.putText(frame, frameTS, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                1, (0, 255, 0), 2, cv2.LINE_AA)

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

        printTimeStats(myTimesBuffer)

        st = datetime.now()
        model_parent_conn.send(pickle.dumps(myFrameBuffer[0]))
        print(f"it took {datetime.now() - st} for putting in the model input queue")

        print()
        print(f"it is {datetime.now()}")
        last_mr = mr

        st = datetime.now()
        mr = modelResult()
        print(f"it took {datetime.now() - st} to get the model result")
        
        st = datetime.now()
        if mr: print("saw someone!!!")
        if mr and not last_mr:
            print("sending last 30 secs")
            writer_input_queue.put((minus30Times + myTimesBuffer,
                                    minus30Frames + myFrameBuffer))
            most_recent_write_time = myTimesBuffer[-1]
        elif mr or last_mr:
            print("sending last 15 secs")
            writer_input_queue.put((myTimesBuffer, myFrameBuffer))
            most_recent_write_time = myTimesBuffer[-1]
        else:
            print("trying to only send 30s old frame")
            if len(minus30Frames) > 0 and minus30Times[0] > most_recent_write_time:
                print(minus30Times[0])
                writer_input_queue.put(([minus30Times[0]], [minus30Frames[0]]))
                most_recent_write_time = minus30Times[0]
        print(f"it took {datetime.now() - st} for putting in the write input queue")

        if select.select([sys.stdin], [], [], 0)[0]:
            if sys.stdin.read(1) == 'q':
                print("got q going to start exiting")
                model_input_queue.put(None)
                writer_input_queue.put(None)
                print("sent Nones, now going to wait 20 seconds for the other workers to exit")
                time.sleep(20)
                print("exiting now")
                sys.exit()

        minus30Frames = myFrameBuffer
        minus30Times = myTimesBuffer
        myFrameBuffer = []
        myTimesBuffer = []

        delayTill100ms()