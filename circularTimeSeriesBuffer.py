import torch
import numpy as np
from datetime import datetime, timedelta, timezone
import sys


class CircularTimeSeriesBuffers:
    def __init__(self, shape, DTYPE):
        #print("initializing")
        self.size = torch.zeros(1, dtype=torch.int32).share_memory_()
        self.size[0] = shape[0]  # Number of time steps
        self.lastbn = torch.zeros(1, dtype=torch.int32).share_memory_()
        self.bn = torch.zeros(1, dtype=torch.int32).share_memory_()

        # Shared memory buffers
        self.nextidxs = torch.zeros((3,1), dtype=torch.int32).share_memory_()  # Most recent index (insertion point)
        self.lengths = torch.zeros((3,1), dtype=torch.int32).share_memory_()
        self.data_buffers = torch.zeros((3,) + shape, dtype=DTYPE).share_memory_()
        self.time_buffers = torch.zeros((3, self.size[0]), dtype=torch.int64).share_memory_()
        #print("initialized")
        sys.stdout.flush()

    def bufferNum(self):
        dt = datetime.now()
        print(dt)
        print(f"bufferNum returning {dt.minute % 3 + (dt.second // 15) % 3}")
        return (dt.minute % 3 + (dt.second // 15) % 3) % 3

    def __setitem__(self, index, value):
        """Set value and timestamp at a circular index."""
        #print("in set item")
        #sys.stdout.flush()
        index = index % self.size[0]  # Ensure circular indexing
        self.data_buffers[self.bn[0]][index] = torch.tensor(value[0])  # Assume value is a tuple (data, timestamp)
        self.time_buffers[self.bn[0]][index] = torch.tensor(int(value[1].replace(tzinfo=timezone.utc).timestamp() * 1e9 
                                                + value[1].microsecond * 1e3))
            
    def __getitem__(self, index):
        """Retrieve (value, timestamp) from a circular index."""
        index = index % self.size[0]  # Ensure circular indexing
        ts_ns = self.time_buffer[index].item()  # Get timestamp in ns
        timestamp = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc)  # Convert back to datetime
        return self.data_buffer[index], timestamp

    def append(self, value, timestamp):
        """Append a new data point with a timezone-aware timestamp (microsecond precision)."""
        #print("in append")
        #sys.stdout.flush()
        # get the current buffer number to use, and reset the old one if we switched
        self.lastbn[0] = self.bn[0].clone()
        self.bn[0] = self.bufferNum()
        if self.bn[0] != self.lastbn[0]:
            self.nextidxs[self.lastbn[0]][0] = 0
            self.lengths[self.bn[0]][0] = 0
        
        self[self.nextidxs[self.bn[0]][0]] = (value, timestamp)  # Use __setitem__
        #print(f"self.nextidx before incrementing {self.nextidx[0]}")
        self.nextidxs[self.bn[0]][0] = self.nextidxs[self.bn[0]][0] + 1  # Move to next index
        self.lengths[self.bn[0]][0] = self.lengths[self.bn[0]][0] + 1
        #print(f"self.nextidx after incrementing {self.nextidx[0]}")
