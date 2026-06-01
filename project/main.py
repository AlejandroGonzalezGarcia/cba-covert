import argparse
import threading
import queue
import time
import signal
import multiprocessing as mp

import stream_unicorn
from buffer import CircularBuffer
import realtime_plot
import data_writer
import decoding
from config import load_config
from psychopy_exp.experiment import run_experiment

def main():
    #TODO: ADD DECODING PARAMETERS, CREATE DECODING FILE

    # ----include argumemt parser for command line
    parser=argparse.ArgumentParser()
    parser.add_argument("--plot", action="store_true", help="Enable real-time plotting") # later accessed as args.plot (args.plot = True if --plot included in command line)
    parser.add_argument("--ps", action="store_true", help="Enable real-time power-spectrum") # same idea for power spectrum (currently not working)
    parser.add_argument("--psychopy", action="store_true", help="Enabled Psychopy simulation") # add argument for psychopy simulation
    parser.add_argument("--decode", action="store_true", help="Enabled decoding") # add argument for real-time decoding
    args = parser.parse_args()
    print(args)

    # -----connect to LSL
    info, inlet = stream_unicorn.connect_to_stream()
    fs = int(info.nominal_srate()) # get sampling rate
    n_ch = info.channel_count() # number of channels

    # ----import parameters from config.yaml
    config = load_config(fs, n_ch)

    # -----shared buffer 
    buf = CircularBuffer(n_samples=2*fs, n_channels=n_ch) # keeps last 2 seconds in it

    # ----stop flag shared by threads
    stop_event = threading.Event() # sync threads with this event (INITIALLY FAlSE)

    # ----create process for plotting
    # store processes
    plot_processes = []
    # define multiprocess queue for data to be transferred between processes
    plot_queue = None

    # create path to store results
    run_dir = data_writer.make_run_directory(config.participant.participant_id)
    print(f"Storing data in {run_dir}")

    # create processes and append to plotting process list if arguments are passed
    if args.plot:
        plot_queue = mp.Queue(maxsize=20) # define queue only if arguments are passed
        plot_proc = mp.Process(
            target=realtime_plot.start_realtime_plotting,
            args=(plot_queue, fs)
        )
        plot_processes.append(plot_proc)
    # if args.ps:
    #     ps_proc = mp.Process(
    #         target=realtime_plot.start_power_spectrum,
    #         args=(plot_queue, fs)
    #     )
    #     plot_processes.append(ps_proc)

    # start plot processes 
    for p in plot_processes:
        p.start()

    # store threads
    threads = []

    # create file writing queue
    # acquisition thread (always opens)
    save_queue = queue.Queue(maxsize=200)
    acq_t = threading.Thread(
        target=stream_unicorn.start_acquisition,
        args=(inlet, buf, stop_event, save_queue, plot_queue),
        daemon=True,
        name="acquisition"
    )
    threads.append(acq_t)

    # thread for writing to csv (always opens)
    save_t = threading.Thread(
        target=data_writer.write_csv,
        args=(
              save_queue, 
              stop_event,
              run_dir),
        daemon=True,
        name="write to csv"
    )
    threads.append(save_t)

    if args.psychopy:
        decision_queue = None
        decode_active = None
        results_queue = None
        # create queue for markers
        marker_queue = queue.Queue(maxsize=200)
        # define thread
        markers_t = threading.Thread(
            target=data_writer.write_markers,
            args=(
                  marker_queue, 
                  stop_event,
                  run_dir),
            daemon=True,
            name="write markers to csv"
        )
        print("Created thread for writing markers")
        threads.append(markers_t)
        if args.decode:
            # create queue for decisions
            decision_queue = queue.Queue(maxsize=1) # only one decision to avoid overloading
            # ----decode flag
            decode_active = threading.Event()
            print("Created decoding event")
            # thread for decisions
            decision_t = threading.Thread(
                target=decoding.decode,
                args=(buf, 
                      decision_queue, 
                      fs, 
                      stop_event, 
                      decode_active, 
                      config.psychopy.stimulus.stimuli_frequencies),
                daemon=True,
                name="decode eeg data"
            )
            print("Created thread for decisions")
            threads.append(decision_t)
            # create queue for results
            results_queue = queue.Queue(maxsize=10)
            # thread for results
            results_t = threading.Thread(
                target=data_writer.write_results,
                args=(
                    results_queue,
                    stop_event,
                    run_dir
                ),
                daemon=True,
                name="store results from psychopy"
            )
            print("Created thread for results")
            threads.append(results_t)

    # -----handle thread stopping
    def handle_sigint(sig, name): # function to handle Ctrl + C
        stop_event.set() # stop_event = True
    
    signal.signal(signal.SIGINT, handle_sigint) # when SIGINT occurs (Ctrl + C) run handle_sigint

    # ----start threads
    for t in threads:
        t.start()

    # ----experiment
    if args.psychopy:
        psychopy_params = config.psychopy
        try:
            run_experiment(
                stop_event=stop_event, 
                marker_queue=marker_queue, 
                decode_active=decode_active,
                decision_queue=decision_queue,
                psychopy_params=psychopy_params,
                participant_id=config.participant.participant_id,
                run_dir=run_dir,
                results_queue=results_queue
                )
        except KeyboardInterrupt:
            stop_event.set()
        finally:
            stop_event.set()

    # -----exit cleanly
    try:
        while not stop_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        stop_event.set()

    # join threads
    for t in threads:
        t.join(timeout=1.0)
    
    # stop plotting
    if plot_queue is not None:
        try:
            plot_queue.put_nowait(None)
        except:
            pass

    # join processes
    for p in plot_processes:
        if p is not None:
            p.join(timeout=1.0)


if __name__ == "__main__":
    main()