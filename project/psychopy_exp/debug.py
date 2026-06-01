
import random
import itertools
from pathlib import Path
from .parameters import build_config
from .utilities import generate_position_sets, get_side_from_position, repeat_images_for_trials

def create_offline_trials(
    num_offline_trials,
    offline_trial_duration,
    images,
    sizes,
    freqs,
    angles,
    radial_distances,
    refresh_hz,
    win=None,
    attention=None,
    shuffle=True,
    ):
        """
        Creates offline trials where:
        - positions are generated from angles and radial distances
        - all stimuli on the left side share one colour/frequency
        - all stimuli on the right side share one colour/frequency
        - left/right colour assignment is counterbalanced
        - left/right frequency assignment is counterbalanced
        - cue colour is varied
        """

        offline_trial_list = []
        print(images)
        sides = ["left", "right"]
        side_to_idx = {
            "left": 0,
            "right": 1
        }

        if len(images) != 2:
            raise ValueError("shapes should have length 2: [left_image, right_image].")

        if len(sizes) != 2:
            raise ValueError("sizes should have length 2: [left_size, right_size].")


        if len(freqs) != 2:
            raise ValueError("freqs should have length 2: one frequency per side.")

        position_sets = generate_position_sets(angles, radial_distances)

        for position_info in position_sets:
            radius = position_info["radius"]
            positions = position_info["positions"]
            angles_for_set = position_info["angles"]

            for img_perm in itertools.permutations(images):
                for freq_perm in itertools.permutations(freqs):
                    # print(freq_perm, img_perm)
                    side_assignment = {}

                    for side_idx, side in enumerate(sides):
                        side_assignment[side] = {
                            "category": img_perm[side_idx],
                            "frequency": freq_perm[side_idx],
                            "size": sizes[side_idx]
                        }
                    # print(side_assignment)
                    condition = []

                    for stim_idx, position in enumerate(positions):
                        side = get_side_from_position(position)
                        side_idx = side_to_idx[side]

                        target_info = {
                            "stim_idx": stim_idx,
                            "side": side,
                            "position": position,
                            "angle": angles_for_set[stim_idx],
                            "radius": radius,

                            # inherited from side-level assignment
                            "category": side_assignment[side]["category"],
                            "frequency": side_assignment[side]["frequency"],
                            "size": sizes[side_idx]
                        }

                        condition.append(target_info)

                    for rep in range(num_offline_trials):
                        for cue_category in images.keys():
                            trial = {
                                "condition": condition,
                                "side_assignment": side_assignment,
                                "cue_category": cue_category,
                                "rep": rep,
                                "duration": offline_trial_duration,
                                "refresh_hz": refresh_hz
                            }

                            offline_trial_list.append(trial)
        print(len(offline_trial_list))

        # if shuffle:
        #     random.shuffle(offline_trial_list)

        # print(f"Total number of trials: {len(offline_trial_list)}")

        # generate list of images corresponding to trials
        trial_images = repeat_images_for_trials(images, len(offline_trial_list))
        # print(trial_images)

        final_list = []

        for i, trial in enumerate(offline_trial_list):
            # print(f"Trial {i+1}")
            # print(trial)
            cue_category=trial['cue_category']
            target_list = []
            for target in trial['condition']:
                target_category = target['category']
                target_img = trial_images[target_category][i]
                print(target)
                print(target_category)
                print(target_img)
                
                # target_list.append(Target(
                #     shape=target['shape'],
                #     size=target['size'],
                #     colour=target['colour'],
                #     freq=target['frequency'],
                #     refresh_hz=refresh_hz,
                #     win=win,
                #     position=target['position']
                # ))
        #     final_list.append(Trial(
        #         target_list=target_list,
        #         refresh_rate=refresh_hz,
        #         duration=offline_trial_duration,
        #         offline=True,
        #         attention="covert",
        #         cue_colour=trial['cue_colour']
        #     ))

        # print(f"Total trials: {len(final_list)}")
        # # return offline_trial_list
        # return final_list


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

# print(images)

params = build_config()
categories = params.stimulus.stimuli_categories

category_images = load_category_images(categories)
    
create_offline_trials(
     params.ssvep.num_offline_trials,
     params.ssvep.offline_trial_duration,
     category_images,
     params.stimulus.stimuli_size,
     params.stimulus.stimuli_frequencies,
     params.stimulus.stimuli_angles,
     params.stimulus.stimuli_distances,
     params.monitor.refresh_rate,
     attention="covert"
)