from pylsl import resolve_byprop, StreamInlet
import numpy as np
import time

def connect_to_stream():
    try:
        streams = resolve_byprop('type', 'EEG', timeout=10)

        print(f"Connected to {streams[0].name()}, {streams[0].type()}")
        print(f"Channels: {streams[0].channel_count()}")
        print(f"Sampling rate: {streams[0].nominal_srate()}")

        info = streams[0]
        inlet = StreamInlet(streams[0])

        print("Created inlet")

        return info, inlet
    except: 
        raise ValueError("Stream not found")

def start_acquisition(inlet, buffer, stop_event, save_queue, plot_queue=None, chunk_size=128, timeout=0.2):
    """
    Pulls EEG chunks from LSL and appends them to buffer that is shared across threads

    parameters
    ------
    inlet: 
        stream inlet
    buffer: CircularBuffer object
        shared buffer object from buffer.py
    stop_event: threading.Event
        signals when acquisition should stop
    chunk_size: int
        maximum number of samples per chunk (note that the number of samples actually pulled depends on timeout)
    timeout: float
        time (s) before pull_chunk times out (chunk will have size of samples corresponding to samples pulled before timeout)
    """

    print(f"starting acquisition with max {chunk_size} samples per chunk")

    total_samples = 0 # keep track of total number of samples
    start_time = time.time()

    while not stop_event.is_set():  
        chunk, timestamps = inlet.pull_chunk(timeout=timeout, max_samples=chunk_size)
        
        if not timestamps:
            continue # in the case where timestamps are not found to prevent errors

        chunk = np.asarray(chunk, dtype=np.float64)

        buffer.append(chunk, timestamps) # append chunk of data to our buffer
        total_samples += chunk.shape[0] # keep track of number of samples acquired

        # send chunk to queue for plotting
        if plot_queue is not None:
            try:
                # print(f"Pushing chunk of size {len(chunk)} to queue")
                plot_queue.put_nowait((chunk, timestamps))
            except: pass
        if save_queue is not None:
            save_queue.put((chunk, timestamps))
            # print(f"pushed chunk of size {len(chunk)} to save queue")

    elapsed = time.time() - start_time
    print(f"Stopped acquisition. Collected {total_samples} samples.")

def get_window_seconds(self, seconds, fs):
    """
    return window for decoding purposes
    """
    return self.get_last(int(seconds*fs))
