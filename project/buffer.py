import numpy as np
import threading

class CircularBuffer:
    def __init__(self, n_samples, n_channels):
        """
        parameters
        -----
        n_samples: int
            total samples stored (t * fs)
        n_channels: int
            number of channels (16 for unicorn EEG)
        """

        self.n_samples = n_samples
        self.channels = n_channels

        self.buffer = np.zeros((n_samples, n_channels)) # predefines array to hold channel data
        self.timestamps = np.zeros(n_samples) # create array of timestamps for samples in buffer
        print(f"Created circular buffer to retain {n_samples} samples at a time")

        self.write_idx = 0
        self.filled = 0

        self.lock = threading.Lock() # lock thread

    def append(self, chunk, timestamps=None):
        """
        add chunk to circular buffer preserving buffer size
        """
        chunk = np.asarray(chunk)
        k = chunk.shape[0]

        # access locked thread
        with self.lock:
            end = self.write_idx + k
            if end <= self.n_samples: # case where end index is less than total number of samples
                self.buffer[self.write_idx:end] = chunk
                if timestamps is not None:
                    self.timestamps[self.write_idx:end] = timestamps
            else: # case where end index exceeds number of samples in buffer (circular behaviour is here)
                first = self.n_samples - self.write_idx
                self.buffer[self.write_idx:] = chunk[:first]
                self.buffer[:end % self.n_samples:] = chunk[first:]
                if timestamps is not None:
                    self.timestamps[self.write_idx:] = timestamps[:first]
                    self.timestamps[:end % self.n_samples] = timestamps[first:]
            
            self.write_idx = end % self.n_samples
            self.filled = min(self.n_samples, self.filled + k)

    def get_last(self, n_samples):
        """
        get n_samples in correct time order
        """

        # access thread-locked buffer
        with self.lock:
            if n_samples > self.filled: # case where we try to pull more samples than our buffer has
                n_samples = self.filled
            start = (self.write_idx - n_samples) % self.n_samples # oldest stored sample at index 0

            if start < self.write_idx: # case where buffer is already in perfect time-order (no circular behaviour)
                return self.buffer[start:self.write_idx]
            else: # case where there is circular behaviour
                return np.vstack((
                    self.buffer[start:],
                    self.buffer[:self.write_idx]
                ))

    def get_all(self):
        """
        get full buffer in time order
        """

        return self.get_last(self.filled)
        


        