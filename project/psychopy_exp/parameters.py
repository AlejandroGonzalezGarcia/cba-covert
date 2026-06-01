import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import List

###########---PROCESSES PARAMETERS AND HANDLES ANY ERRORS
@dataclass
class ParticipantConfig:
    participant_id: str

@dataclass
class MonitorConfig:
    refresh_rate: int
    resolution: List[int]
    window_size: List[int]
    fullscr: bool
    units: str

@dataclass
class SSVEPConfig:
    trial_duration: float
    num_trials: int
    min_trial_duration: float
    waveform: str
    phase_offset: List[int]
    num_offline_trials: int # per condition
    offline_trial_duration: float

@dataclass
class StimulusConfig:
    num_stimuli: int
    stimuli_shapes: List[str]
    stimuli_frequencies: List[int]
    stimuli_angles: List[int]
    stimuli_distances: List[int]
    stimuli_size: List[List[int]]
    stimuli_categories: List[str]


##### handling functions ######
def require_int(x, name):
    if not isinstance(x, (int)):
        raise TypeError(f"{name} must be an integer. input was {x}")

def require_num(x, name):
    if not isinstance(x, (float, int)):
        raise TypeError(f"{name} must be a number (int/float). input was {x}")

def require_array(x, name):
    if not isinstance(x, (list, np.array)):
        raise TypeError(f"{name} must be a list or an array. input: {x}")

def require_array_of_ints(x, name):
    if not isinstance(x, (list, np.array)):
        raise TypeError(f"{name} must be a list or an array. input: {x}")
    for i in range(len(x)-1):
        if not isinstance(x[i], int):
            raise TypeError(f"every index in {x} must be an int. index {i} is {x[i]}.")

def require_array_of_nums(x, name):
    if not isinstance(x, (list, np.array)):
        raise TypeError(f"{name} must be a list or an array. input: {x}")
    for i in range(len(x)-1):
        if not isinstance(x[i], (int, float)):
            raise TypeError(f"every index in {x} must be an int. index {i} is {x[i]}.")
        
def require_bool(x, name):
    if not isinstance(x, bool):
        raise TypeError(f"{name} must be a boolean value. input: {x}")
    
def require_string(x, name):
    if not isinstance(x, str):
        raise TypeError(f"{name} must be a string. input: {x}")
    
def require_array_of_strings(x, name):
    if not isinstance(x, (list)):
        raise TypeError(f"{name} must be a list. input: {x}")
    for i in range(len(x)-1):
        if not isinstance(x[i], str):
            raise TypeError(f"{name} must be contain strings. index {i} is {x[i]}")

##### define config Class #####
@dataclass
class Config:
    participant: ParticipantConfig
    monitor: MonitorConfig
    ssvep: SSVEPConfig
    stimulus: StimulusConfig

    def validate(self):
        #----PARTICIPANT VALIDATION----
        # value validation
        if len(self.participant.participant_id) == 0:
            raise ValueError("participant id must not be empty")
        
        # type validation
        require_string(self.participant.participant_id, "participant id")

        # ----PSYCHOPY MONITOR VALIDATION----
        # VALUE VALIDATION
        if len(self.monitor.resolution) != 2:
            raise ValueError("monitor resolution must be an array of length 2")
        if len(self.monitor.window_size) != 2:
            raise ValueError("window size must be an array of length 2")
        if (self.monitor.units != "pix" and self.monitor.units != "deg"):
            raise ValueError("units must be either 'pix' (pixels) or 'deg' (degrees)")

        # TYPE VALIDATION
        require_int(self.monitor.refresh_rate, "refresh rate")
        require_array_of_ints(self.monitor.resolution, "resolution")
        require_array_of_ints(self.monitor.window_size, "window size")
        require_bool(self.monitor.fullscr, "fullscreen")
        require_string(self.monitor.units, "units")

        # ----PSYCHOPY SSVEP VALIDATION----
        # VALUE VALIDATION
        if (self.ssvep.waveform != "square" and self.ssvep.waveform != "sine"):
            raise ValueError("waveform must be either 'square' or 'sine'")
        
        # TYPE VALIDATION
        require_int(self.ssvep.num_trials, "number of trials")
        require_num(self.ssvep.trial_duration, "trial duration")
        require_num(self.ssvep.min_trial_duration, "minimum trial duration")
        require_array_of_ints(self.ssvep.phase_offset, "phase offset")
        require_string(self.ssvep.waveform, "waveform")
        require_int(self.ssvep.num_offline_trials, "number of offline trials")
        require_num(self.ssvep.offline_trial_duration, "duration of offline trials")

        # ----PSYCHOPY STIMULUS VALIDATION----
        # VALUE VALIDATION
        if not (self.stimulus.num_stimuli == len(self.stimulus.stimuli_shapes) == len(self.stimulus.stimuli_frequencies)
                == len(self.stimulus.stimuli_size)):
            raise ValueError("stimuli number must be equal to the length of arrays for shapes, frequencies, position and size")
        
        # ensure refresh rates are intiger divisors of refresh rate for square waveform
        if self.ssvep.waveform == "square":
            for stim_freq in self.stimulus.stimuli_frequencies:
                if self.monitor.refresh_rate % stim_freq != 0:
                    raise ValueError(f"for square waveform, stimulus frequencies must be integer divisors of refresh rate.\
                                     \nmonitor refresh rate: {self.monitor.refresh_rate}\
                                     \nfrequency that raised error: {stim_freq}")

                # for each frequency, ensure that the number of frames per cycle is even for equal on/off frames
                if (self.monitor.refresh_rate / stim_freq) % 2 != 0:
                    raise ValueError(f"for square waveform, frames per period must be an even number\
                                     \nfrequency that caused error: {stim_freq}\
                                     \n{self.monitor.refresh_rate} / {stim_freq} = {float(self.monitor.refresh_rate / stim_freq)}")
        
        # TYPE VALIDATION
        require_int(self.stimulus.num_stimuli, "number of stimuli")
        require_array_of_strings(self.stimulus.stimuli_shapes, "stimuli shapes")
        require_array_of_nums(self.stimulus.stimuli_frequencies, "stimuli frequencies")
        require_array_of_strings(self.stimulus.stimuli_categories, "stimuli categories")

    
def build_config(params_name='parameters') -> Config:
    # directory where current file lives
    base_dir = Path(__file__).parent

    # path to parameters file
    params_path = base_dir / f"{params_name}.json"
    # print(f"path to parameters file: {params_path}")

    # try catch to open file
    try: 
        with open(f'{params_path}', 'r') as file:
            params = json.load(file)
    except FileNotFoundError:
        print("JSON parameters file not found")
    except json.JSONDecodeError:
        print("Failed to decode parameters JSON from file")

    config = Config(
        participant=ParticipantConfig(**params['participant']),
        monitor=MonitorConfig(**params['monitor']),
        ssvep=SSVEPConfig(**params['ssvep']),
        stimulus=StimulusConfig(**params['stimulus']),
    )
    
    config.validate()
    return config


