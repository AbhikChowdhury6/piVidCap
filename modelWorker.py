import sys
import os
from datetime import datetime, timedelta
import time
from ultralytics import YOLO
import torchvision.transforms as T
import numpy as np

repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")
from circularTimeSeriesBuffer import CircularTimeSeriesBuffers

if os.path.exists(repoPath + "piVidCap/deviceInfo.py"):
    from deviceInfo import modelName, noRecThresh
else:
    modelName = "yolo11s.pt" #default to the small model
    noRecThresh = 8



def model_worker(ctsb: CircularTimeSeriesBuffers, personSignal, exitSignal):
    print("in model worker")
    sys.stdout.flush()
    model = YOLO(modelName)

    while True:
        if exitSignal[0] == 1:
            print("model: got exit signal")
            sys.stdout.flush()
            break

        st = datetime.now()
        secondsToWait = (14 - (st.second % 15)) + (1 - st.microsecond/1_000_000) + .1
        #print(f"model: waiting {secondsToWait} till {st + timedelta(seconds=secondsToWait)}")
        time.sleep(secondsToWait)

        frame = ctsb.data_buffers[ctsb.bn[0]][0]
        #print(f"model: using bufferNum {ctsb.bn[0]}")
        frame = frame.cpu().numpy()  # Convert from torch tensor to numpy
        frame = frame.astype(np.uint8)

        st = datetime.now()
        frame_sum = np.sum(frame)
        #print(f"model: it took {datetime.now() - st} for frame sum to run")
        print(f"model: frame sum is {frame_sum}")
        print(f"model: frame shape is {frame.shape}")
        print(f"model: frame size over shape is {frame_sum / frame.shape}")

        if frame_sum / frame.shape < noRecThresh:
            print("model: frame sum is too low, skipping")
            sys.stdout.flush()
            personSignal[0] = 0
            continue

        try:
            #print("model: going to start running model")
            st = datetime.now()
            r = model(frame, verbose=False)
            print(f"model: it took {datetime.now() - st} for the model to run")

            indexesOfPeople = [i for i, x in enumerate(r[0].boxes.cls) if x == 0]
            if len(indexesOfPeople) > 0:
                #print(f"saw {len(indexesOfPeople)} people")
                sys.stdout.flush()
                maxPersonConf = max([r[0].boxes.conf[i] for i in indexesOfPeople])
                #print(f"the most confident recognition was {maxPersonConf}")
                sys.stdout.flush()
                if maxPersonConf > .25:
                    personSignal[0] = 1
                else:
                    personSignal[0] = 0
            else:
                personSignal[0] = 0
                #print("didn't see anyone")
                sys.stdout.flush()

        except Exception as e:
            print(f"Error processing frame: {e}")
            sys.stdout.flush()
    
    print("model: exiting")
    sys.stdout.flush()
