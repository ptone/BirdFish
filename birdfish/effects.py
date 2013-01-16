"""
Effects classes

added to show because they track themselves over time
have one or more targets that they can apply the effect to in unison

change some attribute over time - generally using envelopes
"""

from birdfish.envelope import Envelope, EnvelopeSegment, StaticEnvelopeSegment
from birdfish.lights import BaseLightElement

# TODO There should probably be a base element - then BaseData or BaseLight element


class BaseEffect(BaseLightElement):
    def __init__(self, *args, **kwargs):
        super(BaseEffect, self).__init__(*args, **kwargs)

class Blink(BaseEffect):

    def __init__(self, targets=[], frequency=2):
        super(Blink, self).__init__()
        self.targets = targets
        self.period_duration = 1.0/(2 * frequency)
        self.blinkon = True
        self.last_changed = None

    def update_targets(self):
        if not self.blinkon:
            # we only modify intensity when off
            for target in self.targets:
                target.set_intensity(0)

    def update(self, show):
        if not self.last_changed:
            self.last_changed = show.timecode
            return
        if show.timecode - self.last_changed > self.period_duration:
            self.blinkon = not self.blinkon
            self.last_changed = show.timecode

        self.update_targets()



class Pulse(BaseEffect):

    def __init__(self, frequency=2):
        # TODO This was a start at blink
        # using an envelope for this is fully overkill
        # but started here and thinking through it
        # leaving as start of pulse effect
        period_duration = 1.0/(2 * frequency)
        on_flash = StaticEnvelopeSegment(start=1, change=0, duration=period_duration)
        off_flash = StaticEnvelopeSegment(start=0, change=0, duration=period_duration)
        self.envelope = Envelope(loop=-1)
        self.envelope.segments = [on_flash, off_flash]

    def update(self, show):
        time_delta = self.get_time_delta(show.timecode)
        if time_delta < 0:
            # negative means a delta hasn't yet be calculated
            return


