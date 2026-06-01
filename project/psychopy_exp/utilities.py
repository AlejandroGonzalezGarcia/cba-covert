from psychopy import visual, event, core, monitors
import time
from pathlib import Path
import json
from pylsl import local_clock
import math
from itertools import cycle, islice

def define_mon(resolution, distance=57.0, width=31.26):
    mon = monitors.Monitor("myMonitor")
    mon.setWidth(width)
    mon.setDistance(distance)
    mon.setSizePix(resolution)
    return mon

def display_message(win, text, display_duration=2.0, location=(0,0), size=1.5):
    message = visual.TextStim(win, text=text, pos=location, height=size)
    message.draw()
    win.flip()
    core.wait(display_duration)

def display_message_key_required(win, text, location=(0,0), size=1.5):
    message = visual.TextStim(win, text=text, pos=location, height=size)
    message.draw()
    win.flip()

    keys = event.waitKeys()

    if keys == 'escape':
        win.close()
        core.quit()


def create_fixation(win, targets, direction_to_look, location=[0,0], attention=None):
        target_of_interest = None
        # get location of fixation
        if len(targets) > 1:
            # if attention is not None:
            #     # take position of target on side of screen told to look at
            #     for target in targets:
            #         if (direction_to_look == "left" and target.position[0] < 0) or (direction_to_look == "right" and target.position[0] > 0): # direction to look left and target also on left
            #             target_of_interest = target
            #             fixation_colour = target.colour
            #     if attention == "overt":
            #         location = target_of_interest.position
            # print(f"location of fixation: {location}")
            if attention=="covert":
                print(f"Creating fixation in the centre")
            for target in targets:
                if (direction_to_look == "left" and target.position[0] < 0) or (direction_to_look == "right" and target.position[0] > 0): # direction to look left and target also on left
                    target_of_interest = target
                    # fixation_colour = target.colour
            # only update location of fixation if attention is overt
            if attention == "overt" or attention is None:
                location = target_of_interest.position
            print(f"location of fixation: {location}")
    

        return visual.TextStim(win, text='+', color="black", height=1.0, pos=location)   

def polar_to_cartesian(radius, angle_deg):
    """
    Converts polar coordinates to x/y coordinates.

    angle convention:
        0   = right
        90  = up
        180 = left
        270 = down
    """
    angle_rad = math.radians(angle_deg)
    x = radius * math.cos(angle_rad)
    y = radius * math.sin(angle_rad)
    return [round(x, 4), round(y, 4)]

def generate_position_sets(angles, radial_distances):
    """
    Creates one position set per radial distance.
    """
    position_sets = []

    for radius in radial_distances:
        positions = [polar_to_cartesian(radius, angle) for angle in angles]

        position_sets.append({
            "radius": radius,
            "positions": positions,
            "angles": angles
        })

    return position_sets

def get_side_from_position(position):
    """
    Classifies a target as left or right based on x-position.
    """
    x, y = position

    if x < 0:
        return "left"
    elif x > 0:
        return "right"
    else:
        raise ValueError(
            f"Position {position} lies on the vertical meridian, so it is neither left nor right."
        )

def load_category_images(categories):
    """
        loads images based on specified category
    """

    # directory where images are located
    base_dir = Path(__file__).resolve().parent / "images"
    # print(base_dir)

    # only allow 2 categories for now
    if len(categories) != 2:
         return ValueError(f"We only accepts 2 categories, input {len(categories)}")


    # account for different image extensions
    valid_extensions = {".png"}

    # define dictionary for different category images
    category_images = {}

    for category in categories:
        # get directory for each category
        category_dir = base_dir / category
        
        if not category_dir.exists():
            raise FileNotFoundError(f"Category folder not found: {category_dir}")

        images = [
             img_path for img_path in category_dir.iterdir() if img_path.suffix.lower() in valid_extensions
        ]

        if len(images) == 0:
             raise FileNotFoundError(f"No image files found in {category_dir}")
        
        category_images[category] = images

    return category_images

def repeat_images_for_trials(category_images, num_trials):
    """
    Expands each category's image list so that it has one image per trial
    if a category has fewer images than the number of trials, images will loop

    params:
    ----
    category_images: dict
        dict where keys are category names and values are lists of image paths
        {
            "faces": [face1, face2]
        }
    
    num_trials: int
        number of trials
    
    returns
    ---
    dict
        dict where each category maps to list of images of length num_trials
    """

    repeated_category_images = {}

    for category, img_paths in category_images.items():
        if len(img_paths) == 0:
            raise ValueError(f"No images found for category {category}")
        
        repeated_category_images[category] = list(
            islice(cycle(img_paths), num_trials)
        )

    return repeated_category_images



def save_results(participant_id, data, folder="results"):
    """
    saves experiment results

    parameters
    ----
    participant_id: str
        participant id
    folder: str
        name of folder where results are stored
    """

    # create folder (one folder PER participant)
    base_dir = Path(__file__).parent
    dir = base_dir / folder
    dir.mkdir(exist_ok=True)

    # file to store results
    file = dir / f"{participant_id}responses.json"
    
    
    # write .json file
    with open(file, "w") as f:
        json.dump(data, f, indent=4)
        print(f"Saved experiment responses to {file}")

def save_to_project(results, run_dir):
    file = Path(run_dir) / "results.json"

    with open(file, "w") as f:
        json.dump(results, f, indent=4)
        print(f"Saved psychopy results to {file}")


def send_marker(marker_queue, event, trial="None", trial_mode="None"):
    """"
    sends marker to queue

    paremeters
    -----
    marker_queue: queue.Queue
        marker queue
    event: str ??
        event (trial start, decision, etc)
    trial: int
        trial number
    trial_mode: str
        online/offline
    """
    if marker_queue is None:
        return
    
    marker = {
        "timestamp": local_clock(), # LSL clock should be synced with that from the main process
        "event": event,
        "trial": trial,
        "trial_mode": trial_mode
    }

    marker_queue.put(marker)
    print(f"Sending marker: {marker['event']}")

def send_result(results_queue, trial_result):
    if results_queue is None:
        return
    
    result = trial_result
    result["timestamp"] = local_clock()
    results_queue.put(result)
    print(f"Sending result from Psychopy")

def send_offline_metadata(offline_queue,
                          metadata):
    
    offline_queue.put(metadata)
    print(f"Sending metadata for offline trial {metadata['trial_num']} of attention time {metadata['attention_mode']}")
    

def decode_flag(decode_active, status):
    if status not in ["start", "stop"]:
        raise ValueError("argument to update decode status must be either 'start' or 'stop'")
    if status == "start":
        decode_active.set()
        print("Started decoding")
    elif status == "stop":
        decode_active.clear()
        print("Stopped decoding")
