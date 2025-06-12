import sys
import os
from datetime import datetime, timedelta
import time
import torchvision.transforms as T
import torch
import numpy as np
from ultralytics import YOLO
import cv2

import torch.nn.functional as F

import matplotlib.pyplot as plt


def normalize_frame(frame):
    frame = frame - frame.min()
    frame = frame / (frame.max() + 1e-5)
    return (frame * 255).astype('uint8')

def animate_frames(frames, pause_time=0.2):
    # Convert first frame to numpy and normalize
    frame = frames[0].cpu().numpy()
    frame = normalize_frame(frame)

    # Create figure and display first frame
    fig, ax = plt.subplots()
    im = ax.imshow(frame, cmap='gray' if frame.ndim == 2 else None, vmin=0, vmax=255)
    ax.axis('off')

    for i in range(1, len(frames)):
        frame = frames[i].cpu().numpy()
        frame = normalize_frame(frame)
        im.set_data(frame)
        fig.canvas.draw()
        plt.pause(pause_time)

    plt.close(fig)
    
repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")
from circularTimeSeriesBuffer import CircularTimeSeriesBuffers
from logUtils import worker_configurer
import logging

if os.path.exists(repoPath + "piVidCap/deviceInfo.py"):
    from deviceInfo import capType, buffSecs, debugLvl, capHz
else:
    print("error no deviceInfo found")
    sys.exit()




def model_worker(ctsb: CircularTimeSeriesBuffers, personSignal, exitSignal, log_queue):
    worker_configurer(log_queue)
    l = logging.getLogger("model_worker")
    l.setLevel(debugLvl)
    l.info("Model worker started")

    def downsample_frames(frames, size=(360, 640)):
        l.debug("frames shape %s", str(frames.shape))
        frames = frames.permute(0, 3, 1, 2).float()  # [T, C, H, W]
        frames = F.interpolate(frames, size=size, mode='bilinear', align_corners=False)
        return frames.permute(0, 2, 3, 1)  # [T, H, W, C]

    def compute_avg_exp_diff(frames):
        diffs = (frames[1:] - frames[:-1]).abs()  # shape: [T-1, H, W, C]
        l.debug("avg diffs %f", diffs.float().mean())
        l.debug(str(diffs[0]))
        thresholded = torch.where(diffs > 100, diffs, torch.zeros_like(diffs))
        l.debug("thresholded mean %f", thresholded.float().mean() )

        animate_frames(diffs, pause_time=0.7)


        return thresholded.float().mean().item()  # scal1ar

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
            l.debug("FrameMeanresult: %f\t threshold: %d", m, self.thresh)
            sys.stdout.flush()
            
            return int(m > self.thresh)
        
        def getSqDiffresult(self, ctsb):
            #do the sum of the diff squared
            buffNum = (ctsb.bn[0] + 2) % 3
            l.debug('buffNum %d', buffNum)
            frames = ctsb.data_buffers[buffNum][::capHz]
            frames = frames[:-1]
            l.debug("num frames to look at %d", len(frames))
            
            frames = frames.to(dtype=torch.int16)
            #frames = downsample_frames(frames, size=(45, 80))
            motion_score = compute_avg_exp_diff(frames)
            l.debug(motion_score)



            firstFrame = ctsb.data_buffers[buffNum][0]
            firstFrame = firstFrame.cpu().numpy().astype(np.int16)
            l.debug("first frame sum: %d", firstFrame.sum())

            l.debug('ctsb.lengths[buffNum] %d', ctsb.lengths[buffNum])
            l.debug('last index ctsb.lengths[buffNum]-1 %d', ctsb.lengths[buffNum]-1)
            lastFrame = ctsb.data_buffers[buffNum][ctsb.lengths[buffNum]-1]
            lastFrame = lastFrame.cpu().numpy().astype(np.int16)
            l.debug("last frame sum: %d", lastFrame.sum())

            diffFrame = lastFrame - firstFrame
            l.debug(np.abs(diffFrame).mean())
            sqDiff = diffFrame ** 2

            avgsqDiff = sqDiff.mean()
            l.debug("sqDiffMeanresult: %f\t threshold: %d",avgsqDiff, self.thresh)

            return int(avgsqDiff > self.thresh)



        def __init__(self, capType):
            self.recType = capType.split('-')[0]
            if self.recType == 'yolo':
                self.model = YOLO(capType.split('-')[1])
                self.getResult = self.getYOLOresult
            
            if self.recType == 'frameMean':
                self.thresh = int(capType.split('-')[1])
                self.getResult = self.getFrameMeanresult
                
            if self.recType == 'sqDiff':
                self.thresh = int(capType.split('-')[1])
                self.getResult = self.getSqDiffresult
        
    
    d = detect(capType)

    while True:
        if exitSignal[0] == 1:
            l.info("got exit signal")
            sys.stdout.flush()
            break
        
        st = datetime.now()
        secondsToWait = ((buffSecs-1) - (st.second % buffSecs)) + (1 - st.microsecond/1_000_000) + .1
        #print(f"model: waiting {secondsToWait} till {st + timedelta(seconds=secondsToWait)}")
        time.sleep(secondsToWait)
        st = datetime.now()
        personSignal[0] = d.getResult(ctsb)

        l.debug("it took %s for the model to run", str(datetime.now() - st))
        sys.stdout.flush()
    
    l.info("exiting")
    sys.stdout.flush()
