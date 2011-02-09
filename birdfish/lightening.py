from lights import *
import random

class Lightening(LightGroup):
    # @@ this needs to be reconfigured as an effect
    #
    def __init__(self, *args, **kwargs):
        super(Lightening, self).__init__(*args, **kwargs)
        self.macro_next = 0
        self.micro_next = 0
        self.intensity = 0
        self.flashing = False
        self.bout = False
        self.flash_count = 3
    
    def update(self,show):
        if self.intensity:
            if not self.macro_next:
                self.macro_next = show.timecode
            if not self.micro_next:
                self.micro_next = show.timecode
            if self.macro_next <= show.timecode:
                if not self.bout:
                    # flash a random number of times
                    self.flash_count = random.randint(3,6)
                    self.bout = True
                elif self.flash_count == 0:
                    self.macro_next = show.timecode + random.randint(7,14)
                    self.bout = False
                    return
                # we are in for a bout
                if self.bout and self.micro_next <=show.timecode:
                    if self.flashing:
                        # trigger is on superclass
                        self.trigger(0)
                        self.flashing = False
                        self.flash_count -= 1
                        self.micro_next = show.timecode + 1.0 / random.randint(5,25)
                    else:
                        intensity = random.randint(100,255)
                        self.trigger(intensity)
                        self.flashing = True
                        self.micro_next = show.timecode + .04
            else:
                # wait
                return


    def signal(self,message):
        """receive a midi message and trigger"""
        vel = message[0][2]
        self.intensity = (vel*2)
        if not self.intensity:
            if self.flashing:
                self.trigger(0)
                self.flashing = False
            if self.bout:
                self.bout = False
            self.macro_next = 0
            self.micro_next = 0
