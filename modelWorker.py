import sys
import os
from datetime import datetime, timedelta
import time
import torchvision.transforms as T
import numpy as np
from ultralytics import YOLO

repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")
from circularTimeSeriesBuffer import CircularTimeSeriesBuffers
from logUtils import worker_configurer
import logging

if os.path.exists(repoPath + "piVidCap/deviceInfo.py"):
    from deviceInfo import capType, buffSecs
else:
    print("error no deviceInfo found")
    sys.exit()



def model_worker(ctsb: CircularTimeSeriesBuffers, personSignal, exitSignal, debugLvl, log_queue):
    worker_configurer(log_queue)
    logger = logging.getLogger("model_worker")
    logger.info("Model worker started")

    class detect:
        def getYOLOresult(self, frame):
            frame = ctsb.data_buffers[ctsb.bn[0]][0]
            frame = frame.cpu().numpy().astype(np.uint8)
            r = self.model(frame, verbose=False)
            try:
                indexesOfPeople = [i for i, x in enumerate(r[0].boxes.cls) if x == 0]
                if len(indexesOfPeople) > 0:
                    #print(f"saw {len(indexesOfPeople)} people")
                    sys.stdout.flush()
                    maxPersonConf = max([r[0].boxes.conf[i] for i in indexesOfPeople])
                    #print(f"the most confident recognition was {maxPersonConf}")
                    sys.stdout.flush()
                    if maxPersonConf > .25:
                        return 1
                    else:
                        return 0
                else:
                    return 0
                    #print("didn't see anyone")
                    sys.stdout.flush()

            except Exception as e:
                print(f"Error processing frame: {e}")
                sys.stdout.flush()
                return 0

        def getFrameMeanresult(self, ctsb):
            frame = ctsb.data_buffers[ctsb.bn[0]][0]
            frame = frame.cpu().numpy()  # Convert from torch tensor to numpy
            frame = frame.astype(np.uint8)

            m = frame.mean()
            logger.debug("FrameMeanresult: %d\t threshold: %d", m, self.thresh)
            sys.stdout.flush()
            
            return int(m > self.thresh)
        
        def getDiffresult(self, ctsb):
            #do the sum of the diff squared
            logger.debug('ctsb.bn[0] %d', ctsb.bn[0])
            firstFrame = ctsb.data_buffers[ctsb.bn[0]][0]
            firstFrame = firstFrame.cpu().numpy().astype(np.uint8)
            logger.debug("first frame sum: %d", firstFrame.sum())

            logger.debug('ctsb.lengths[ctsb.bn[0]] %d', ctsb.lengths[ctsb.bn[0]])
            lastFrame = ctsb.data_buffers[ctsb.bn[0]][ctsb.lengths[ctsb.bn[0]]]
            lastFrame = lastFrame.cpu().numpy().astype(np.uint8)
            logger.debug("last frame sum: %d", lastFrame.sum())

            sqDiff = (lastFrame - firstFrame) ** 2

            avgsqDiff = sqDiff.mean()
            logger.debug("sqDiffMeanresult: %d\t threshold: %d",avgsqDiff, self.thresh)

            return int(avgsqDiff > self.thresh)



        def __init__(self, capType):
            self.recType = capType.split('-')[0]
            if self.recType == 'yolo':
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
            logger.info("got exit signal")
            sys.stdout.flush()
            break
        
        st = datetime.now()
        secondsToWait = ((buffSecs-1) - (st.second % buffSecs)) + (1 - st.microsecond/1_000_000) + .1
        #print(f"model: waiting {secondsToWait} till {st + timedelta(seconds=secondsToWait)}")
        time.sleep(secondsToWait)
        st = datetime.now()
        personSignal[0] = d.getResult(ctsb)

        logger.debug("it took %s for the model to run", str(datetime.now() - st))
        sys.stdout.flush()
    
    logger.info("exiting")
    sys.stdout.flush()
