import sys
import os
from datetime import datetime, timedelta
import time
from ultralytics import YOLO
import torchvision.transforms as T

repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")
from circularTimeSeriesBuffer import CircularTimeSeriesBuffer

if os.path.exists(repoPath + "piVidCap/deviceInfo.py"):
    from deviceInfo import modelName
else:
    modelName = "yolo11s.pt" #default to the small model



def model_worker(ctsb: CircularTimeSeriesBuffer, personSignal, exitSignal):
    print("in model worker")
    sys.stdout.flush()
    model = YOLO(modelName)

    while True:
        if exitSignal[0] == 1:
            print("model worker got exit signal")
            sys.stdout.flush()
            break

        st = datetime.now()
        secondsToWait = (14 - (st.second % 15)) + (1 - st.microsecond/1_000_000)
        print(f"model waiting {secondsToWait} till {st + timedelta(seconds=secondsToWait)}")
        time.sleep(secondsToWait)

        frames, times = ctsb.get_last_15_seconds()
        print(f"len of frames in model {len(frames)}")
        if len(frames) == 0:
            continue

        frame = frames[0].cpu().numpy()  # Convert from torch tensor to numpy
        frame = frame.astype(np.uint8)

        # frame = frames[0].permute(2, 0, 1)

        # target_size=(640, 640)
        # c, h, w = frame.shape
        # target_h, target_w = target_size

        # scale = min(target_w / w, target_h / h)
        # new_w, new_h = int(w * scale), int(h * scale)
        
        # transform_resize = T.Resize((new_h, new_w))
        # frame = transform_resize(frame)
        
        # pad_w = (target_w - new_w) // 2
        # pad_h = (target_h - new_h) // 2

        # transform_pad = T.Pad((pad_w, pad_h, target_w - new_w - pad_w, target_h - new_h - pad_h), fill=0)
        # frame = transform_pad(frame)

        # frame = frame.unsqueeze(0)

        try:
            print("going to start running model")
            st = datetime.now()
            r = model(frame, verbose=True)
            print(f"it took {datetime.now() - st} for the model to run")

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
    
    print("model worker exiting")
    sys.stdout.flush()
