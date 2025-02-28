from ultralytics import YOLO
import sys
import os
from datetime import datetime
# import cv2
repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")
from deviceInfo import modelName


def model_worker(input_queue, output_queue):
    print("in model worker")
    sys.stdout.flush()
    model = YOLO(modelName)

    while True:
        frame = input_queue.get()  # Get frame from the input queue
        if frame is None:  # None is the signal to exit
            print("exiting model worker")
            sys.stdout.flush()
            break

        try:
            st = datetime.now()
            r = model(frame, verbose=False)
            print(f"it took {datetime.now() - st} for the model to run")

            indexesOfPeople = [i for i, x in enumerate(r[0].boxes.cls) if x == 0]
            ret = False
            if len(indexesOfPeople) > 0:
                #print(f"saw {len(indexesOfPeople)} people")
                sys.stdout.flush()
                maxPersonConf = max([r[0].boxes.conf[i] for i in indexesOfPeople])
                #print(f"the most confident recognition was {maxPersonConf}")
                sys.stdout.flush()
                if maxPersonConf > .25:
                    ret = True
            else:
                #print("didn't see anyone")
                sys.stdout.flush()
            
            #print(f"sending {ret}")
            sys.stdout.flush()
            output_queue.put(ret)
            del r
            del frame
        except Exception as e:
            print(f"Error processing frame: {e}")
            sys.stdout.flush()
    
    print("model worker exiting")
    sys.stdout.flush()
