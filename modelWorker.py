import sys
import os
from datetime import datetime, timedelta
import time
import torchvision.transforms as T
import numpy as np

repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")
from circularTimeSeriesBuffer import CircularTimeSeriesBuffers

if os.path.exists(repoPath + "piVidCap/deviceInfo.py"):
    from deviceInfo import capType, buffSecs
else:
    print("error no deviceInfo found")
    sys.exit()



def model_worker(ctsb: CircularTimeSeriesBuffers, personSignal, exitSignal, debugLvl):
    print("in model worker")
    sys.stdout.flush()

    class detect:
        def getYOLOresult(self, frame):
            r = self.model(ctsb.data_buffers[ctsb.bn[0]][0], verbose=False)
            try:
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

        def getFrameMeanresult(self, ctsb):
            frame = ctsb.data_buffers[ctsb.bn[0]][0]
            frame = frame.cpu().numpy()  # Convert from torch tensor to numpy
            frame = frame.astype(np.uint8)

            m = frame.mean()
            print(f"MODEL: FrameMeanresult: {m}\t threshold: {self.thresh}")
            sys.stdout.flush()
            
            return m > self.thresh
        
        def getDiffresult(self, ctsb):
            #do the sum of the diff squared
            firstFrame = ctsb.data_buffers[ctsb.bn[0]][0]
            firstFrame = firstFrame.cpu().numpy().astype(np.uint8)
            lastFrame = ctsb.data_buffers[ctsb.bn[0]][ctsb.lengths[ctsb.bn[0]]]
            lastFrame = lastFrame.cpu().numpy().astype(np.uint8)
            sqDiff = (lastFrame - firstFrame) ** 2

            avgsqDiff = sqDiff.mean()
            print(f"MODEL: sqDiffMeanresult: {avgsqDiff}\t threshold: {self.thresh}")
            sys.stdout.flush()

            return avgsqDiff > self.thresh



        def __init__(self, capType):
            self.recType = capType.split('-')[0]
            if self.recType == 'yolo':
                from ultralytics import YOLO
                self.model = YOLO(capType.split('-')[1])
                self.getResult = self.getYOLOresult
            
            if self.recType == 'frameMean':
                self.thresh = int(capType.split('-')[1])
                self.getResult = self.getFrameMeanresult
                
            if self.recType == 'diff':
                self.thresh = int(capType.split('-')[1])
                self.getResult = self.getDiffresult
        
    
    d = detect(capType)

    while True:
        if exitSignal[0] == 1:
            print("model: got exit signal")
            sys.stdout.flush()
            break
        
        st = datetime.now()
        secondsToWait = ((buffSecs-1) - (st.second % buffSecs)) + (1 - st.microsecond/1_000_000) + .1
        #print(f"model: waiting {secondsToWait} till {st + timedelta(seconds=secondsToWait)}")
        time.sleep(secondsToWait)

        personSignal[0] = d.getResult(ctsb)

        print(f"model: it took {datetime.now() - st} for the model to run")
        sys.stdout.flush()
    
    print("model: exiting")
    sys.stdout.flush()
