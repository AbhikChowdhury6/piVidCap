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
import pickle

repoPath = "/home/pi/Documents/"
sys.path.append(repoPath + "piVidCap/")

import torch
import torch.multiprocessing as mp

from modelWorker import model_worker
from writerWorker import writer_worker
from deviceInfo import subSample



# Define buffer properties
BUFFER_SIZE = 450  # Maximum number of frames stored
HEIGHT = 1080  # Frame height
WIDTH = 1920   # Frame width
CHANNELS = 3   # RGB color channels
DTYPE = np.uint8

# Compute shared memory size
frame_size = HEIGHT * WIDTH * CHANNELS
total_size = BUFFER_SIZE * frame_size

frame_buffer = torch.zeros((BUFFER_SIZE, HEIGHT, WIDTH, CHANNELS), dtype=DTYPE).share_memory_()
frame_index = torch.zeros(1, dtype=torch.int64).share_memory_()  # Single index tracker
time_buffer = torch.zeros(BUFFER_SIZE, dtype="datetime64[ns]").share_memory_()
person_buffer = torch.zeros(BUFFER_SIZE // 150, dtype=type(True)).share_memory_()





def health_checks():
    if not (model_process.is_alive() and writer_process.is_alive()):
        print(f"is model alive?: {model_process.is_alive()}")
        print(f"is writer alive?: {writer_process.is_alive()}")
        print("one of the processes died exiting everything")
        model_parent_conn.send(pickle.dumps(None))
        writer_parent_conn.send(pickle.dumps(None))
        return False
    return True


if __name__ == "__main__":
    while True:
        
        if select.select([sys.stdin], [], [], 0)[0]:
            if sys.stdin.read(1) == 'q':
                print("got q going to start exiting")
                model_parent_conn.send(pickle.dumps(None))
                writer_parent_conn.send(pickle.dumps(None))
                print("sent Nones, now going to wait 20 seconds for the other workers to exit")
                time.sleep(20)
                print("exiting now")
                sys.exit()
        
        delayTill100ms()