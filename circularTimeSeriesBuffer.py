import torch
from datetime import datetime, timedelta, timezone


class CircularTimeSeriesBuffer:
    def __init__(self, shape, DTYPE):
        self.size = shape[0]  # Number of time steps
        self.nextidx = 0  # Most recent index (insertion point)
        self.wrapped = False  # Tracks if buffer has wrapped around

        # Shared memory buffers
        self.data_buffer = torch.zeros(shape, dtype=DTYPE).share_memory_()
        self.time_buffer = torch.zeros(self.size, dtype=torch.int64).share_memory_()  # Store timestamps in ns
        print("initialized")

    def __setitem__(self, index, value):
        """Set value and timestamp at a circular index."""
        print("in set item")
        index = index % self.size  # Ensure circular indexing
        self.data_buffer[index] = torch.tensor(value[0])  # Assume value is a tuple (data, timestamp)
        self.time_buffer[index] = torch.tensor(int(value[1].replace(tzinfo=timezone.utc).timestamp() * 1e9 
                                                + value[1].microsecond * 1e3))
            
    def __getitem__(self, index):
        """Retrieve (value, timestamp) from a circular index."""
        index = index % self.size  # Ensure circular indexing
        ts_ns = self.time_buffer[index].item()  # Get timestamp in ns
        timestamp = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc)  # Convert back to datetime
        return self.data_buffer[index], timestamp

    def append(self, value, timestamp):
        """Append a new data point with a timezone-aware timestamp (microsecond precision)."""
        print("in append")
        self[self.nextidx] = (value, timestamp)  # Use __setitem__
        self.nextidx = (self.nextidx + 1) % self.size  # Move to next index
        if self.nextidx == 0:
            self.wrapped = True  # Mark buffer as wrapped when cycling back

    def lastidx(self):
        return (self.nextidx + self.size -1) % self.size

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