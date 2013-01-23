"""
Effects classes

added to show because they track themselves over time
have one or more targets that they can apply the effect to in unison

change some attribute over time - generally using envelopes
"""
from collections import OrderedDict
import random
from birdfish.envelope import Envelope, EnvelopeSegment, StaticEnvelopeSegment
from birdfish.lights import BaseLightElement, LightElement
from birdfish import tween

# TODO There should probably be a base element - then BaseData or BaseLight element


class BaseEffect(BaseLightElement):
    def __init__(self, *args, **kwargs):
        super(BaseEffect, self).__init__(*args, **kwargs)
        self.targets = kwargs.get('targets', [])
        # TODO shoud triggered default be T or F?
        triggered = kwargs.get('triggered', True)
        if triggered:
            self.trigger_state = 0
        else:
            self.trigger_state = 1

    def trigger(self, intensity, **kwargs):
        if intensity:
            self.trigger_state = 1
        else:
            self.trigger_state = 0

class ColorShift(BaseEffect):
    # TODO notes:
    # how does it handle the existing color of an element
    # can I handle explicit start color, or take current color and shift both
    # can we reset the color to the original?
    #
    def __init__(self, shift_amount=0, target=0, **kwargs):
        super(ColorShift, self).__init__(**kwargs)
        # a list of dictionaries for shift info
        self.shifts = []
        self.hue_envelope = Envelope(loop=-1)
        self.sat_envelope = Envelope(loop=-1)

    def _add_shift(self, start, end, duration, shape, envelope):
        change = end - start
        seg = EnvelopeSegment(
                start=start,
                change=change,
                duration=duration,
                tween=shape,
                )
        envelope.segments.append(seg)

    def add_hue_shift(self, start=0, end=1, duration=5, shape=tween.LINEAR):
        self._add_shift(start, end, duration, shape, self.hue_envelope)

    def add_sat_shift(self, start=0, end=1, duration=5, shape=tween.LINEAR):
        self._add_shift(start, end, duration, shape, self.sat_envelope)

    def update(self, show, targets=None):
        if self.trigger_state:
            if not targets:
                targets = self.targets
            elif isinstance(targets, LightElement):
                targets = [targets]
            hue = self.hue_envelope.update(show.time_delta)
            sat = self.sat_envelope.update(show.time_delta)
            for target in targets:
                target.hue = hue
                target.saturation = sat


class Twinkle(BaseEffect):
    def __init__(self, frequency=2, **kwargs):
        super(Twinkle, self).__init__(**kwargs)
        self.on_min = .01
        self.on_max = 1
        self.off_min = .8
        self.off_max = 1.3
        self.intensity_min = .3
        self.intensity_max = 1
        self.blinkon = True
        self.cycle_elapsed = 0
        self.last_changed = None
        # the parameters of current cycle
        self.on_dur = self.off_dur = self.intensity = 0
        self.durations = {True:self.on_dur, False:self.off_dur}
        # self.setup_cycle()

    def setup_cycle(self):
        self.on_dur = self.on_min + random.random() * (self.on_max - self.on_min)
        self.off_dur = self.off_min + random.random() * (self.off_max - self.off_min)
        self.intensity = self.intensity_min + random.random() * (self.intensity_max - self.intensity_min)
        self.durations = {True:self.on_dur, False:self.off_dur}

    def update(self, show, targets=None):
        # note, currently can not easily assign a twinkle to an elements effects
        # array - must add it to the show directly as it uses the trigger method
        # this is true of any effect that uses trigger method of elements for
        # rendering the effect
        self.trigger_state = 1
        if self.trigger_state:
            if not targets:
                targets = self.targets
            elif isinstance(targets, LightElement):
                targets = [targets]
            self.cycle_elapsed += show.time_delta
            if self.cycle_elapsed > self.durations[self.blinkon]:
                # current cycle complete
                if self.blinkon:
                    # trigger off targets
                    [t.trigger(0) for t in targets]
                    self.setup_cycle()
                else:
                    [t.trigger(self.intensity) for t in targets]

                self.blinkon = not self.blinkon
                self.cycle_elapsed = 0

        def _off_trigger(self):
            print "twinkle off trigger"
            super(Twinkle, self)._off_trigger()
            # only works for explicit effect targets
            [t.trigger(0) for t in self.targets]
            self.trigger_state = 1


class Blink(BaseEffect):

    def __init__(self, frequency=2, **kwargs):
        super(Blink, self).__init__(**kwargs)
        self.period_duration = 1.0/(2 * frequency)
        self.blinkon = True
        self.last_changed = None

    def update(self, show):
        if not self.last_changed:
            self.last_changed = show.timecode
            return
        if show.timecode - self.last_changed > self.period_duration:
            self.blinkon = not self.blinkon
            self.last_changed = show.timecode
        if not self.blinkon:
            # we only modify intensity when off
            for target in self.targets:
                target.set_intensity(0)

class Pulser(BaseEffect):

    # TODO need to implement trigger here - otherwise effects will run
    # "in the background" all the time,and may not be synced to
    # elements as desired.
    #
    def __init__(self, frequency=1, on_shape=tween.LINEAR, off_shape=tween.LINEAR, **kwargs):
        super(Pulser, self).__init__(**kwargs)
        period_duration = 1.0/(2 * frequency)
        on_flash = EnvelopeSegment(start=0, change=1, tween=on_shape, duration=period_duration)
        off_flash = EnvelopeSegment(start=1, change=-1, tween=off_shape, duration=period_duration)
        self.envelope = Envelope(loop=-1)
        self.envelope.segments = [on_flash, off_flash]

    def update(self, show, targets=None):
        if self.trigger_state:
            if not targets:
                targets = self.targets
            elif isinstance(targets, LightElement):
                targets = [targets]
            val = self.envelope.update(show.time_delta)
            for target in targets:
                target.set_intensity(val * target.intensity)


