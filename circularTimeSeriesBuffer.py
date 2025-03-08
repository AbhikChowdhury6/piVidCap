import torch
from datetime import datetime, timedelta, timezone
import sys


class CircularTimeSeriesBuffer:
    def __init__(self, shape, DTYPE):
        #print("initializing")
        self.size = torch.zeros(1, dtype=torch.int32).share_memory_()
        self.size[0] = shape[0]  # Number of time steps
        self.nextidx = torch.zeros(1, dtype=torch.int32).share_memory_()  # Most recent index (insertion point)
        self.wrapped = torch.zeros(1, dtype=torch.bool).share_memory_()
        self.wrapped[0] = False  # Tracks if buffer has wrapped around

        # Shared memory buffers
        self.data_buffer = torch.zeros(shape, dtype=DTYPE).share_memory_()
        self.time_buffer = torch.zeros(self.size[0], dtype=torch.int64).share_memory_()  # Store timestamps in ns
        #print("initialized")
        sys.stdout.flush()

    def __setitem__(self, index, value):
        """Set value and timestamp at a circular index."""
        #print("in set item")
        sys.stdout.flush()
        index = index % self.size[0]  # Ensure circular indexing
        self.data_buffer[index] = torch.tensor(value[0])  # Assume value is a tuple (data, timestamp)
        self.time_buffer[index] = torch.tensor(int(value[1].replace(tzinfo=timezone.utc).timestamp() * 1e9 
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
        sys.stdout.flush()
        self[self.nextidx[0]] = (value, timestamp)  # Use __setitem__
        #print(f"self.nextidx before incrementing {self.nextidx[0]}")
        self.nextidx[0] = (self.nextidx[0] + 1) % self.size[0]  # Move to next index
        #print(f"self.nextidx after incrementing {self.nextidx[0]}")
        if self.nextidx[0] == 0:
            self.wrapped[0] = True  # Mark buffer as wrapped when cycling back

    def lastidx(self):
        return (self.nextidx[0] + self.size[0] -1) % self.size[0]

    def get_sorted_view(self):
        """Returns a sorted logical view of timestamps and values without copying memory."""
        if not self.wrapped[0]:
            return self.data_buffer[:self.nextidx[0]], self.time_buffer[:self.nextidx[0]]
        else:
            indices = torch.cat((torch.arange(self.nextidx[0], self.size[0]), torch.arange(0, self.nextidx[0])))
            return self.data_buffer[indices], self.time_buffer[indices]

    def get_last_n_seconds(self, seconds):
        """Retrieve the last `seconds` worth of data & timestamps (with nanosecond precision)."""
        if self.nextidx[0] == 0 and not self.wrapped[0]:
            return torch.empty(0), torch.empty(0)  # No data in buffer

        sorted_values, sorted_timestamps = self.get_sorted_view()
        ts_threshold_ns = int((datetime.now(timezone.utc) - timedelta(seconds=seconds)).timestamp() * 1e9)

        # Binary search for the earliest timestamp >= ts_threshold_ns
        idx = torch.searchsorted(sorted_timestamps, torch.tensor(ts_threshold_ns), side="left").item()
        dtList = [datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc) for ts_ns in sorted_timestamps[idx:]]
        return sorted_values[idx:], dtList

    def get_last_15_seconds(self):
        return self.get_last_n_seconds(15)

    def get_last_30_seconds(self):
        return self.get_last_n_seconds(30)