import numpy as np
from psychopy import visual

class Target:
    def __init__(self, category, img, size, freq, refresh_hz, win, position=[0,0]):
        self.size = size
        self.win = win
        self.position = position
        self.direction = "centre" # default
        self.freq = freq
        self.refresh_hz = refresh_hz
        self.img = img
        self.category=category

        self.frames_per_cycle = self.refresh_hz // self.freq
        
        # create image
        self.stim = visual.ImageStim(
            win=win,
            image=str(self.img),
            pos=position,
            size=self.size,
            mask="circle"
        )

    
    def update_position(self):
        if self.shape == "square":
            self.stim = visual.Rect(
                self.win,
                width=self.size[0],
                height=self.size[1],
                pos=self.position,
                fillColor=self.colour,
            )
        elif self.shape == "circle":
            self.stim = visual.Circle(
                win=self.win,
                radius=self.size,
                pos=self.position,
                fillColor=self.colour
            )
        elif self.shape == "triangle":
            self.stim = visual.Polygon(
                win=self.win,
                edges=3,
                radius=self.size,
                pos=self.position,
                fillColor=self.colour
            )
        if self.position[0] > 0:
            self.direction = "right"
        elif self.position[0] < 0:
            self.direction = "left"
    

    def draw_target(self):
        self.stim.draw()


    def is_on_this_frame(self, frameN, frames_per_cycle):
        # determines whether the target is on in the current frame
        half_period = int((frames_per_cycle / 2))

        # we will start counting from frame = 0 
        phase = frameN % int(frames_per_cycle)

        # return true if we are at the first half of the cycle (the ON phase)
        return phase < half_period

    def describe_target(self):
        desc = f"Target Description:\n\
    Shape: {self.shape}\n\
    Colour: {self.colour}\n\
    Frequency: {self.freq}"
        print(desc)