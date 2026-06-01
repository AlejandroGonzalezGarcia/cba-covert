import time
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from buffer import CircularBuffer
import queue

import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore

def start_realtime_plotting(
        plot_queue, 
        fs, 
        plot_duration=1.0, 
        n_channels=8, 
        update_interval=0.05):
    """
    Real-time plotting of EEG data using PyQtGraph.

    Parameters
    ----------
    plot_queue : multiprocessing.Queue
        Queue carrying tuples of (chunk, timestamps). Send (None, None) to stop.
    fs : int
        Sampling frequency in Hz.
    plot_duration : float
        Seconds of recent data to display.
    n_channels : int
        Number of EEG channels to display.
    update_interval : float
        Plot refresh interval in seconds.
    """
    print("Started plotting")
    window_samples = int (plot_duration * fs)
    buffer_capacity = max(window_samples * 2, window_samples + 1)

    try:
        buf = CircularBuffer(buffer_capacity, 16)
    except Exception as e:
        print(f"Error creating plotting buffer: {e}")

    # don't sacrifice performance for smoother lines
    pg.setConfigOptions(antialias=False)

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    
    win = pg.GraphicsLayoutWidget(show=True, title="Real-time Unicorn EEG")
    win.resize(1200, 900)

    x = np.linspace(0, plot_duration, window_samples)

    plots = []
    curves = []

    for ch in range(n_channels):
        p = win.addPlot(row=ch, col=0) # creates PlotItem object
        p.showGrid(x=True, y=True, alpha=0.2)
        p.setLabel("left", f"EEG{ch+1}")
        if ch == 0:
            p.setTitle("Amplitude")
        if ch == n_channels - 1:
            p.setLabel("bottom", f"Last {plot_duration}s of data")
        
        # start with fixed x range, let y be initialized
        p.setXRange(0, plot_duration, padding=0.0)
        p.setYRange(-500000, 500000, padding=0.0)

        curve = p.plot(x, np.zeros(window_samples)) # create PlotDataItem object

        plots.append(p)
        curves.append(curve)

    class RealtimePlotter(QtCore.QObject):
        def __init__(self):
            super().__init__()
            self.running = True
        
        def update(self):
            while self.running:
                try:
                    chunk, timestamps = plot_queue.get_nowait()
                except queue.Empty:
                    break
            
                if chunk is None and timestamps is None:
                    self.running = False
                    win.close()
                    app.quit()
                    return
            
                buf.append(chunk, timestamps)

            data = buf.get_last(window_samples)
            if data.shape[0] < window_samples:
                return
            
            eeg = data[:, :n_channels]

            for ch in range(n_channels):
                curves[ch].setData(x, eeg[:, ch])
    
    plotter = RealtimePlotter()

    timer = QtCore.QTimer()
    timer.timeout.connect(plotter.update)
    timer.start(int(update_interval * 1000))

    win.show()
    app.exec()
    print("Stopped plotting")

# start_realtime_plotting(None, 250, plot_duration=1.0, n_channels=8, update_interval=0.05)


# def start_realtime_plotting(plot_queue, fs, plot_duration=1.0, n_channels=8, update_interval=0.05):
#     """
#     real-time plotting of EEG data obtained from buffer

#     parameters
#     ----
#     plot_queue: multiprocessing Queue object
#         queue that holds chunks of data defined in main
#     fs: int
#         sampling frequency (Hz)
#     n_channels: int
#         number of EEG channels (8 for unicorn)
#     update_interval: float
#         time between plot refreshes in seconds
#     """
#     # TODO: FINE REASONABLE Y-BOUNDS OR A WAY OF DETERMINING THEM DYNAMICALLY OR PER SESSION
#     # TODO: PLOT ONLY DESIRED CHANNELS

#     window_samples = int(plot_duration * fs)

#     # give plotting buffer a margin beyond displayed window
#     buffer_capacity = max(window_samples * 2, window_samples + 1)
#     try:
#         buf = CircularBuffer(buffer_capacity, 16) # define buffer for plotting
#     except Exception as e:
#         print(f"Error creating plotting buffer {e}")
#         return
    

#     plt.ion() # real time
#     # create one plot for each channel
#     fig, axes = plt.subplots(n_channels, 1, figsize=(12,10), sharex=True)

#     # ensure axes is always indexable even for q channel
#     if n_channels == 1:
#         axes = [axes]

#     # x = np.arange(window_samples) # time array
#     x = np.linspace(0, plot_duration, window_samples)
#     lines = [] # store EEG signals
 
#     # define plot properties
#     for i in range(n_channels):
#         line, = axes[i].plot(x, np.zeros(window_samples))
#         axes[i].set_ylabel(f"EEG{i+1}", rotation=0, labelpad=25)
#         axes[i].set_ylim(-500000,500000) # NOT CHOSEN FOR CAP BEING WORN
#         lines.append(line)
#     axes[-1].set_xlabel(f"Last {plot_duration}s of Data")
#     axes[-1].set_xticks([0, 0.5, 1], minor=False)
#     axes[0].set_title("Amplitude")

#     plt.tight_layout()
#     plt.show(block=False)

#     print("Started real-time plotting")

#     last_draw = time.perf_counter()
#     running = True
#     try:
#         while running:
#             try:
#                 chunk, timestamps = plot_queue.get(timeout=0.1)

#                 # sentinel for shutdown
#                 if chunk is None:
#                     break

#                 buf.append(chunk, timestamps)

#             except queue.Empty:
#                 pass

#             now = time.perf_counter()
#             if now - last_draw >= update_interval:
#                 data = buf.get_last(window_samples)

#                 if data.shape[0] >= window_samples:
#                     eeg = data[:, :n_channels]

#                     for i in range(n_channels):
#                         lines[i].set_ydata(eeg[:, i])

#                     fig.canvas.draw_idle()
#                     fig.canvas.flush_events()

#                 last_draw = now

#             plt.pause(0.001)

#     except Exception as e:
#         print(f"Failed to plot: {e}")

#     finally:
#         plt.ioff()
#         plt.close(fig)
#         print("Stopped real-time plotting")

            # # in case buffer does not have enough samples yet, skip iterations until we have enough
            # if data.shape[0] < window_samples:
            #     plt.pause(update_interval)
            #     continue

            # # plot EEG channels only
            # for i in range(n_channels):
            #     lines[i].set_ydata(data[:,i])
            # # print(f" average: {[float(np.mean(data[:,i])) for i in range(n_channels)]}")
            
            # # redraw
            # now = time.time()
            # if now - last_draw >= update_interval:
            #     fig.canvas.draw()
            #     fig.canvas.flush_events()
            #     last_draw = now
    # except Exception as e:
    #     print(f"Failed to plot {e}")
    
    # finally:
    #     plt.ioff()
    #     plt.close(fig)
    #     print("Stopped real-time plotting")

# def start_power_spectrum(plot_queue, fs, plot_duration=2.0, n_channels=8, update_interval=0.1, fmax=100):
#     """
#     real time power spectrum for EEG from shared buffer

#     parameters
#     -----
#     plot_queue: multiprocessing.Queue 
#         queue of data from main script
#     fs: int
#         sampling frequency in Hz
#     plot_duration: float
#         length of EEG window used to calculate power spectrum
#     n_channels: int
#         number of EEG channels to plot
#     update_interval: float
#         time between redraws
#     fmax: float
#         maximum frequency to show
#     """
#     # TODO: FINE REASONABLE Y-BOUNDS OR A WAY OF DETERMINING THEM DYNAMICALLY OR PER SESSION
#     # TODO: PLOT ONLY DESIRED CHANNELS
#     #-----------I DO NOT KNOW IF THIS WORKS WELL YET (CAP HASN'T BEEN WORN)----------------

#     window_samples = int(plot_duration * fs) # window of EEG samples
#     try:
#         buf = CircularBuffer(500, 16) # define buffer for plotting
#     except Exception as e:
#         print(f"Error creating plotting buffer {e}")

#     # real-time plotting
#     plt.ion()
#     fig, axes = plt.subplots(n_channels, 1, figsize=(12, 10), sharex=True)

#     nperseg = fs
#     noverlap = nperseg//2
#     freqs, _ = signal.welch(
#         np.zeros(window_samples),
#         fs=fs,
#         nperseg=nperseg,
#         noverlap=noverlap
#     )
#     freq_mask = freqs <= fmax # create mask for frequencies that fall below our maximum
#     freqs_plot = freqs[freq_mask] # extract only frequencies that we will use

#     lines = []
#     for i in range(n_channels):
#         line, = axes[i].plot(freqs_plot, np.zeros_like(freqs_plot))
#         axes[i].set_ylabel(f"EEG {i+1}", rotation=0, labelpad=25)
#         axes[i].set_xlim(0, fmax)
#         lines.append(line)
    
#     axes[0].set_title("Power Spectrum (Welch)")
#     axes[-1].set_xlabel("Frequency (Hz)")

#     plt.tight_layout()
#     plt.show()
#     print("Started Power Spectrum")
#     last_draw = 0.0
#     try: 
#         while True:
#             # retrieve chunk from queue
#             chunk, timestamp = plot_queue.get()

#             if chunk is None:
#                 break
#             buf.append(chunk, timestamp)
#             data = buf.get_last(window_samples)

#             # in case buffer does not have enough samples yet, skip iterations until we have enough
#             if data.shape[0] < window_samples:
#                 plt.pause(update_interval)
#                 continue
            
#             eeg = data[:, :n_channels] # get EEG data

#             for i in range(n_channels):
#                 x = eeg[:,i]
#                 x = x - np.mean(x) # demean
#                 # power spectrum using welch
#                 freqs, psd = signal.welch(
#                     x,
#                     fs=fs,
#                     nperseg=nperseg,
#                     noverlap=noverlap
#                 )

#                 psd_plot = psd[freq_mask] # only take PSD values corresponding to freqs of interest
#                 lines[i].set_ydata(psd_plot)

#             now = time.time()
#             if now - last_draw >= update_interval:
#                 fig.canvas.draw()
#                 fig.canvas.flush_events()
#                 last_draw = now
#     except Exception as e:
#         print(f"Plotting error for power spectrum: {e}")
    
#     finally:
#         plt.ioff()
#         plt.close(fig)
#         print("Stopped power spectrum plot")
