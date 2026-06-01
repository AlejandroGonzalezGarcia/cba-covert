import csv
from pathlib import Path
import numpy as np
import os
import queue
from datetime import datetime
import re

def make_run_directory(participant_id, folder="results"):
    """
    Create a unique folder with format:
    YYYY-MM-DD-participantID-iteration

    Iteration increases only for runs by the same participant on the same day
    """
    # get directory we are in
    base_dir = Path(__file__).parent

    # create path to results folder within current directory
    results_dir = base_dir / folder
    results_dir.mkdir(exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    prefix = f"{today}-{participant_id}-"

    # begin counting amount of times predix shows up in results folder
    max_iter = 0

    for path in results_dir.iterdir():
        # print(path)
        if not path.is_dir():
            continue
        
        # get final component of file path (file name)
        name = path.name

        # if the file name does not start with the existing prefix defined above, skip iteration
        if not name.startswith(prefix):
            continue
        
        # match YYYY-MM-DD-participantID-N
        match = re.fullmatch(
            rf"{re.escape(today)}-{re.escape(participant_id)}-(\d+)",
            name
        )
        if match:
            iteration = int(match.group(1))
            if iteration > max_iter:
                max_iter = iteration
        
    next_iter = max_iter + 1
    run_dir = results_dir / f"{today}-{participant_id}-{next_iter}"
    run_dir.mkdir(exist_ok=False)

    return run_dir


def write_csv(save_queue, stop_event, run_dir):
    """
    takes chunks of EEG data from a queue and adds it to a csv file for the specified participant

    parameters
    -----
    participant_id: str
        participant id
    save_queue: queue.Queue 
        queue for threads that holds EEG data
    stop_event: threading.Event
        stop event for threads
    folder: str
        name of folder holding results 
    """
    file = Path(run_dir) / "eeg.csv"

    # create csv header for unicorn EEG
    header = [
        "EEG1", "EEG2", "EEG3", "EEG4",
        "EEG5", "EEG6", "EEG7", "EEG8",
        "AccX", "AccY", "AccZ", 
        "GyroX", "GyroY", "GyroZ",
        "Battery", "Counter",
        "Timestamp"
    ]

    with open(file, mode='w', newline='') as f:
        # create csv writer
        writer = csv.writer(f)

        # create columns
        writer.writerow(header)
        print(f"Writing eeg data to file: {file}")
        while not stop_event.is_set():
            chunk, timestamps = save_queue.get()

            data = np.column_stack((chunk, timestamps))
            writer.writerows(data)
    return

def write_markers(marker_queue, stop_event, run_dir):
    """
    writes markers to a separate csv file. these markers can later be lined up with data collection

    parameters
    -----
    participant_id: str
        participant id
    marker_queue: queue.Queue
        queue that stores markers
    stop_event: threading.Event
        event that signals threads to end processes
    folder: str
        folder where csv file for markers will be stored
    """

    file = Path(run_dir) / "markers.csv"
    # csv header
    header = ["timestamp", 
              "event", 
              "trial", 
              "trial_mode"] # trial mode is offline/online 

    with open(file, mode='w', newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        print(f"Writing markers to file {file}")
        while not stop_event.is_set():
            # try catch to fetch marker from marker queue
            try:
                marker = marker_queue.get()
                # print(f"Got marker from queue: {marker}")
            except queue.Empty: # wait for marker to arrive
                continue
            
            # if marker queue contains nothing, break out of loop
            if marker is None:
                break
        
            # get row data from marker
            row = {
                "timestamp": marker.get("timestamp"),
                "event": marker.get("event"),
                "trial": marker.get("trial"), #trial num
                "trial_mode": marker.get("trial_mode") #offline/online
            }
            # write to csv
            writer.writerow(row)
            # flush f
            f.flush()

def write_offline_metadata(offline_queue, stop_event, run_dir):
    """
    stores metadata for offline trials (direction to look)
    each offline trial will include:
    dierction to look,
    """
    file = Path(run_dir) / "offline_trials.csv"

    # csv header
    header = [
        "trial",
        "attention_mode", # overt (fixate) / covert (do not fixate)
        "target_colour",
        "target_frequency",
        "target_side",
        "left_colour",
        "left_frequency",
        "right_colour",
        "right_frequency"
    ]



def write_results(results_queue, stop_event, run_dir):
    file = Path(run_dir) / "results.csv"

    # csv header
    header = [
        "trial",
        "target_direction",
        "target_frequency",
        "response_direction",
        "response_frequency",
        "rt",
        "correct",
        "timestamp"
    ]

    with open(file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        print(f"Writing results to file: {file}")

        while not stop_event.is_set():
            try:
                result = results_queue.get()
                print("Received result from Psychopy")
            except queue.Empty:
                continue

            writer.writerow([
                result["trial"],
                result["target_direction"],
                result["target_frequency"],
                result["response"],
                result["response_frequency"],
                result["rt"],
                result["correct"],
                result["timestamp"]
            ])
            f.flush()







