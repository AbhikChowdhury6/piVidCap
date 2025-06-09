import time
import select
import sys
import os
import torch
import torch.multiprocessing as mp
from datetime import datetime

repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")


from modelWorker import model_worker
from writerWorker import writer_worker
from piVidCap import pi_vid_cap
from circularTimeSeriesBuffer import CircularTimeSeriesBuffers
if os.path.exists(repoPath + "piVidCap/deviceInfo.py"):
    from deviceInfo import subSample, debugLvl, buffSecs, capHz, maxWidth, maxHeight
else:
    print("error no deviceInfo found")
    sys.exit()



# Define buffer properties
BUFFER_SIZE = (buffSecs * capHz) + 3  # Maximum number of frames stored
HEIGHT = maxHeight // subSample # Frame height
WIDTH = maxWidth // subSample  # Frame width
CHANNELS = 3   # RGB color channels
DTYPE = torch.uint8

tsVidBuffer = CircularTimeSeriesBuffers((BUFFER_SIZE, HEIGHT, WIDTH, CHANNELS), DTYPE)
exitSignal = torch.zeros(1, dtype=torch.int64).share_memory_()
personSignal = torch.zeros(1, dtype=torch.int8).share_memory_()
dLvl = torch.zeros(1, dtype=torch.int8).share_memory_()
dLvl[0] = debugLvl

vidCap_process = mp.Process(target=pi_vid_cap, args=(tsVidBuffer, exitSignal, dLvl))
vidCap_process.start()

model_process = mp.Process(target=model_worker, args=(tsVidBuffer, personSignal, exitSignal, dLvl))
model_process.start()

writer_process = mp.Process(target=writer_worker, args=(tsVidBuffer, personSignal, exitSignal, dLvl))
writer_process.start()


def closeOut():
    exitSignal[0] = 1
    print("set exit signal to 1, now going to wait 20 seconds for the other workers to exit")
    time.sleep(buffSecs + 5)
    print("exiting now")
    sys.exit()


if __name__ == "__main__":
    print("in main")
    while True:
        #print("in mainloop")
        if not (model_process.is_alive() and writer_process.is_alive()
                and vidCap_process.is_alive()):
            print(f"is vidCap alive?: {vidCap_process.is_alive()}")
            print(f"is model alive?: {model_process.is_alive()}")
            print(f"is writer alive?: {writer_process.is_alive()}")
            print("one of the processes died exiting everything")
            closeOut()
        
        if select.select([sys.stdin], [], [], 0)[0]:
            if sys.stdin.read(1) == 'q':
                print("got q going to start exiting")
                closeOut()

        time.sleep(1)