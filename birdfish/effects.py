"""
Effects classes

added to show because they track themselves over time
have one or more targets that they can apply the effect to in unison

change some attribute over time - generally using envelopes
"""

from birdfish.envelope import Envelope, EnvelopeSegment, StaticEnvelopeSegment
from birdfish.lights import BaseLightElement, LightElement
from birdfish import tween

# TODO There should probably be a base element - then BaseData or BaseLight element


class BaseEffect(BaseLightElement):
    def __init__(self, *args, **kwargs):
        super(BaseEffect, self).__init__(*args, **kwargs)
        self.targets = kwargs.get('targets', [])

class Blink(BaseEffect):

    def __init__(self, frequency=2, **kwargs):
        super(Blink, self).__init__(**kwargs)
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



class Pulser(BaseEffect):

    # TODO need to implement trigger here - otherwise effects will run
    # "in the background" all the time,and may not be synced to
    # elements as desired.
    #
    def __init__(self, frequency=1, on_shape=tween.LINEAR, off_shape=tween.LINEAR, triggered=True, **kwargs):
        super(Pulser, self).__init__(**kwargs)
        period_duration = 1.0/(2 * frequency)
        on_flash = EnvelopeSegment(start=0, change=1, tween=on_shape, duration=period_duration)
        off_flash = EnvelopeSegment(start=1, change=-1, tween=off_shape, duration=period_duration)
        self.envelope = Envelope(loop=-1)
        self.envelope.segments = [on_flash, off_flash]
        if triggered:
            self.trigger_state = 0
        else:
            self.trigger_state = 1

    def update(self, show, targets=None):
        if not targets:
            targets = self.targets
        elif isinstance(targets, LightElement):
            targets = [targets]

        if self.trigger_state:
            time_delta = self.get_time_delta(show.timecode)
            if time_delta < 0:
                # negative means a delta hasn't yet be calculated
                return
            val = self.envelope.update(time_delta)
            # print val
            for target in targets:
                target.set_intensity(val * target.intensity)

    def trigger(self, intensity, **kwargs):
        if intensity:
            self.trigger_state = 1
        else:
            self.trigger_state = 0

