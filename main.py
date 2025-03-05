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

#i'd like this to be a timestamp synced buffer
# of some data type and the timestamps associated with them
import torch
from datetime import datetime, timedelta

import torch
from datetime import datetime, timezone, timedelta

class CircularTimeSeriesBuffer:
    def __init__(self, shape, DTYPE):
        self.size = shape[0]  # Number of time steps
        self.nextidx = 0  # Most recent index (insertion point)
        self.wrapped = False  # Tracks if buffer has wrapped around

        # Shared memory buffers
        self.data_buffer = torch.zeros(shape, dtype=DTYPE).share_memory_()
        self.time_buffer = torch.zeros(self.size, dtype=torch.int64).share_memory_()  # Store timestamps in ns

    def __setitem__(self, index, value):
        """Set value and timestamp at a circular index."""
        index = index % self.size  # Ensure circular indexing
        self.data_buffer[index] = value[0]  # Assume value is a tuple (data, timestamp)
        self.time_buffer[index] = int(value[1].replace(tzinfo=timezone.utc).timestamp() * 1e9 + value[1].microsecond * 1e3)

    def __getitem__(self, index):
        """Retrieve (value, timestamp) from a circular index."""
        index = index % self.size  # Ensure circular indexing
        ts_ns = self.time_buffer[index].item()  # Get timestamp in ns
        timestamp = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc)  # Convert back to datetime
        return self.data_buffer[index], timestamp

    def append(self, value, timestamp):
        """Append a new data point with a timezone-aware timestamp (microsecond precision)."""
        self[self.nextidx] = (value, timestamp)  # Use __setitem__
        self.nextidx = (self.nextidx + 1) % self.size  # Move to next index
        if self.nextidx == 0:
            self.wrapped = True  # Mark buffer as wrapped when cycling back

    def get_sorted_view(self):
        """Returns a sorted logical view of timestamps and values without copying memory."""
        if not self.wrapped:
            return self.data_buffer[:self.nextidx], self.time_buffer[:self.nextidx]
        else:
            indices = torch.cat((torch.arange(self.nextidx, self.size), torch.arange(0, self.nextidx)))
            return self.data_buffer[indices], self.time_buffer[indices]

    def get_last_n_seconds(self, seconds):
        """Retrieve the last `seconds` worth of data & timestamps (with nanosecond precision)."""
        if self.nextidx == 0 and not self.wrapped:
            return torch.empty(0), torch.empty(0)  # No data in buffer

        sorted_values, sorted_timestamps = self.get_sorted_view()
        ts_threshold_ns = int((datetime.now(timezone.utc) - timedelta(seconds=seconds)).timestamp() * 1e9)

        # Binary search for the earliest timestamp >= ts_threshold_ns
        idx = torch.searchsorted(sorted_timestamps, torch.tensor(ts_threshold_ns), side="left").item()
        return sorted_values[idx:], sorted_timestamps[idx:]

    def get_last_15_seconds(self):
        return self.get_last_n_seconds(15)

    def get_last_30_seconds(self):
        return self.get_last_n_seconds(30)


# Example usage
buffer = CircularTimeSeriesBuffer((450, 3), torch.float32)  # Buffer storing 3D data
now = datetime.now(timezone.utc).replace(microsecond=123456)  # Ensure microsecond precision

# Simulate inserting data
for i in range(300):
    buffer.append(torch.tensor([i, i + 1, i + 2]), now - timedelta(seconds=i))

# Retrieve last 15s and 30s of data
values_15s, timestamps_15s = buffer.get_last_15_seconds()
values_30s, timestamps_30s = buffer.get_last_30_seconds()

# Convert timestamps back to datetime with microsecond precision
timestamps_15s = [datetime.fromtimestamp(ts.item() / 1e9, tz=timezone.utc) for ts in timestamps_15s]
timestamps_30s = [datetime.fromtimestamp(ts.item() / 1e9, tz=timezone.utc) for ts in timestamps_30s]

print("Last 15 seconds:", len(values_15s), timestamps_15s[:3])
print("Last 30 seconds:", len(values_30s), timestamps_30s[:3])

# Example usage
buffer = CircularTimeSeriesBuffer((450, 3), torch.float32)  # Buffer storing 3D data
now = datetime.now().replace(microsecond=0)

# Simulate inserting data
for i in range(300):
    buffer.append(torch.tensor([i, i + 1, i + 2]), now - timedelta(seconds=i))

# Retrieve last 15s and 30s of data
values_15s, timestamps_15s = buffer.get_last_15_seconds()
values_30s, timestamps_30s = buffer.get_last_30_seconds()

print("Last 15 seconds:", values_15s.shape, timestamps_15s.shape)
print("Last 30 seconds:", values_30s.shape, timestamps_30s.shape)



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
exitSignal = torch.zeros(1, dtype=torch.int64).share_memory_()
time_buffer = torch.zeros(BUFFER_SIZE, dtype="datetime64[ns]").share_memory_()
personSignal = torch.zeros(1, dtype=type(True)).share_memory_()





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