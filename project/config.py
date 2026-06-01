import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Union, List
import numpy as np

# ----DEFINE DATACLASSES
@dataclass
class StreamConfig:
    max_chunk_size: int
    timeout: float

@dataclass
class BufferConfig:
    buffer_duration: Union[float, int]

@dataclass
class PlotTimeConfig:
    plot_duration: Union[float, int]
    n_channels: int

@dataclass
class ParticipantConfig:
    participant_id: str

# ---psychopy experiment parameters 
@dataclass
class MonitorConfig:
    refresh_rate: int
    resolution: List[int]
    window_size: List[int]
    fullscr: bool
    units: str

@dataclass
class SSVEPConfig:
    num_trials: int
    trial_duration: float
    min_trial_duration: float
    waveform: str
    phase_offset: List[Union[int, float]]

@dataclass
class StimulusConfig:
    num_stimuli: int
    stimuli_shapes: List[str]
    stimuli_frequencies: List[Union[int, float]]
    stimuli_position: List[List[Union[int, float]]]
    stimuli_size: List[Union[int, float]]

@dataclass
class PsychopyConfig:
    monitor: MonitorConfig
    ssvep: SSVEPConfig
    stimulus: StimulusConfig

# ----HELPER VALIDATION FUNCTIONS---
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

@dataclass
class Config:
    stream: StreamConfig
    buffer: BufferConfig
    plot_time: PlotTimeConfig
    participant: ParticipantConfig
    psychopy: PsychopyConfig

    def validate(self, fs, n_ch):
        """
        parameter validation

        parameters
        --------
        fs: int
            sampling frequency 
        n_ch: int
            number of eeg channels
        """
        # ----STREAM PARAMETER VALIDATION----
        # VALUE VALIDATION
        if self.stream.max_chunk_size <= 0:
            raise ValueError("max stream chunk size must be > 0")
        if self.stream.max_chunk_size > fs:
            raise ValueError("keep sampling chunk size smaller than sampling frequency")
        if self.stream.timeout <= 0:
            raise ValueError("timeout for stream collection must be > 0")
        
        # TYPE VALIDATION
        require_int(self.stream.max_chunk_size, "maximum chunk size")
        require_num(self.stream.timeout, "stream timeout")
        
        # ----BUFFER PARAMETER VALIDATION----
        # VALUE VALIDATION
        if self.buffer.buffer_duration <= 0:
            raise ValueError("buffer duration must be > 0")
        
        # TYPE VALIDATION
        require_num(self.buffer.buffer_duration, "buffer duration")
        
        # ----PLOTTING PARAMETER VALIDATION----
        # VALUE VALIDATION
        if self.plot_time.plot_duration <= 0:
            raise ValueError("plot duration time must be > 0")
        if self.plot_time.n_channels <= 0:
            raise ValueError("n_channels for plotting must be > 0 (disable plotting if you do not wish to plot)")
        if self.plot_time.n_channels > n_ch:
            raise ValueError(f"number of channels for plotting must be < {n_ch} for this eeg device")
        if self.plot_time.plot_duration > self.buffer.buffer_duration:
            raise ValueError("plot duration must be < buffer duration. decrease plot duration or increase buffer duration")
        
        # TYPE VALIDATION
        require_num(self.plot_time.plot_duration, "plot duration")
        require_int(self.plot_time.n_channels, "number of channels")

        # ----PARTICIPANT PARAMETER VALIDATION----
        # VALUE VALIDATION
        if len(self.participant.participant_id) == 0:
            raise ValueError("participant ID must not be an empty string")
        
        # TYPE VALIDATION
        require_string(self.participant.participant_id, "participant ID")
        
        # ----PSYCHOPY MONITOR VALIDATION----
        # VALUE VALIDATION
        if len(self.psychopy.monitor.resolution) != 2:
            raise ValueError("monitor resolution must be an array of length 2")
        if len(self.psychopy.monitor.window_size) != 2:
            raise ValueError("window size must be an array of length 2")
        if (self.psychopy.monitor.units != "pix" and self.psychopy.monitor.units != "deg"):
            raise ValueError("units must be either 'pix' (pixels) or 'deg' (degrees)")

        # TYPE VALIDATION
        require_int(self.psychopy.monitor.refresh_rate, "refresh rate")
        require_array_of_ints(self.psychopy.monitor.resolution, "resolution")
        require_array_of_ints(self.psychopy.monitor.window_size, "window size")
        require_bool(self.psychopy.monitor.fullscr, "fullscreen")
        require_string(self.psychopy.monitor.units, "units")

        # ----PSYCHOPY SSVEP VALIDATION----
        # VALUE VALIDATION
        if (self.psychopy.ssvep.waveform != "square" and self.psychopy.ssvep.waveform != "sine"):
            raise ValueError("waveform must be either 'square' or 'sine'")
        
        # TYPE VALIDATION
        require_int(self.psychopy.ssvep.num_trials, "number of trials")
        require_num(self.psychopy.ssvep.trial_duration, "trial duration")
        require_num(self.psychopy.ssvep.min_trial_duration, "minimum trial duration")
        require_array_of_ints(self.psychopy.ssvep.phase_offset, "phase offset")
        require_string(self.psychopy.ssvep.waveform, "waveform")

        # ----PSYCHOPY STIMULUS VALIDATION----
        # VALUE VALIDATION
        if not (self.psychopy.stimulus.num_stimuli == len(self.psychopy.stimulus.stimuli_shapes) == len(self.psychopy.stimulus.stimuli_frequencies)
                == len(self.psychopy.stimulus.stimuli_size)):
            raise ValueError("stimuli number must be equal to the length of arrays for shapes, frequencies, position and size")
        
        # ensure refresh rates are intiger divisors of refresh rate for square waveform
        if self.psychopy.ssvep.waveform == "square":
            for stim_freq in self.psychopy.stimulus.stimuli_frequencies:
                if self.psychopy.monitor.refresh_rate % stim_freq != 0:
                    raise ValueError(f"for square waveform, stimulus frequencies must be integer divisors of refresh rate.\
                                     \nmonitor refresh rate: {self.psychopy.monitor.refresh_rate}\
                                     \nfrequency that raised error: {stim_freq}")

                # for each frequency, ensure that the number of frames per cycle is even for equal on/off frames
                if (self.psychopy.monitor.refresh_rate / stim_freq) % 2 != 0:
                    raise ValueError(f"for square waveform, frames per period must be an even number\
                                     \nfrequency that caused error: {stim_freq}\
                                     \n{self.psychopy.monitor.refresh_rate} / {stim_freq} = {float(self.psychopy.monitor.refresh_rate / stim_freq)}")
        
        # TYPE VALIDATION
        require_int(self.psychopy.stimulus.num_stimuli, "number of stimuli")
        require_array_of_strings(self.psychopy.stimulus.stimuli_shapes, "stimuli shapes")
        require_array_of_nums(self.psychopy.stimulus.stimuli_frequencies, "stimuli frequencies")

# --------LOAD PARAMETERS
def load_config(fs, n_ch) -> Config:
    """
    loads parameters from config.yaml

    paremeters
    ------
    fs: int
        eeg sampling frequency
    n_ch: int
        number of eeg channels
    """
    path = Path("config.yaml")

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    # create Config object by accessing values of data dictionary
    config = Config(
        stream=StreamConfig(**data['stream']),
        buffer=BufferConfig(**data['buffer']),
        plot_time=PlotTimeConfig(**data['plot_time']),
        participant=ParticipantConfig(**data['participant']),
        psychopy=PsychopyConfig(
            monitor=MonitorConfig(**data["psychopy"]["monitor"]),
            ssvep=SSVEPConfig(**data["psychopy"]["ssvep"]),
            stimulus=StimulusConfig(**data["psychopy"]["stimulus"]),
        ),
    )

    # validate parameters
    config.validate(fs, n_ch)
    return config
