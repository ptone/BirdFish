"""
Effects classes

added to show because they track themselves over time
have one or more targets that they can apply the effect to in unison

change some attribute over time - generally using envelopes
"""
from collections import OrderedDict
import random
from birdfish.envelope import (Envelope, EnvelopeSegment,
        StaticEnvelopeSegment, ColorEnvelope)
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
        self.envelope_filters = []

    def filter_targets(self, targets):
        """
        subclasses can override to provide some behavior that limits
        the effect only to some targets, or targets in some state
        """
        # TODO may need to rething to make it easier to add filters
        # and or reuse this adsr stuff
        if targets and self.envelope_filters:
            filtered_targets = []
            for target in targets:
                if hasattr(target, 'adsr_envelope'):
                    label = target.adsr_envelope.get_current_segment().label
                    if label in self.envelope_filters:
                        filtered_targets.append(target)
            return filtered_targets
        else:
            return targets

    def get_targets(self, targets):
        if not targets:
            targets = self.targets
        elif isinstance(targets, LightElement):
            targets = [targets]
        # set self.targets for use by _off_trigger or other
        # methods outside the update call
        self.targets = self.filter_targets(targets)
        return self.targets

    def trigger(self, intensity, **kwargs):
        if intensity:
            self.trigger_state = 1
            self._on_trigger(intensity, **kwargs)
        else:
            self.trigger_state = 0
            self._off_trigger(intensity, **kwargs)

    def _off_trigger(self, intensity, **kwargs):
        # Since effects can act on lights during release - after off-trigger
        # they may be responsible for turning element intensity off
        super(BaseEffect, self)._off_trigger()
        for element in self.targets:
            element.set_intensity(0)

class ColorShift(BaseEffect, ColorEnvelope):
    # TODO notes:
    # how does it handle the existing color of an element
    # can I handle explicit start color, or take current color and shift both
    # can we reset the color to the original?
    #
    def __init__(self, shift_amount=0, target=0, **kwargs):
        super(ColorShift, self).__init__(**kwargs)
        ColorEnvelope.__init__(self, **kwargs)

    def _on_trigger(self, intensity, **kwargs):
        self.reset()

    def update(self, show, targets=None):
        if self.trigger_state:
            targets = self.get_targets(targets)
            hue, sat, intensity = self._color_update(show.time_delta)
            for target in targets:
                if hue is not None:
                    target.hue = hue
                if sat is not None:
                    target.saturation = sat
                if intensity is not None:
                    target.set_intensity(intensity)


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
        # rendering the effect - basically an effect can not be piggy-backed on
        # an elements trigger, if it is to use trigger to cause/manage the effect
        # perhaps an effect should always manipulate the lower level attributes
        # instead of using a trigger
        self.trigger_state = 1
        if self.trigger_state:
            targets = self.get_targets(targets)
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
            # only works for explicit effect targets
            [t.trigger(0) for t in self.targets]
            self.trigger_state = 1


class Blink(BaseEffect):

    def __init__(self, frequency=2, **kwargs):
        super(Blink, self).__init__(**kwargs)
        self._frequency = frequency
        self.blinkon = True
        self.last_changed = None
        self._set_frequency(self._frequency)

    def update(self, show, targets=None):
        targets = self.get_targets(targets)
        if not self.last_changed:
            self.last_changed = show.timecode
            return
        if show.timecode - self.last_changed > self.period_duration:
            self.blinkon = not self.blinkon
            self.last_changed = show.timecode
        if not self.blinkon:
            # we only modify intensity when off
            for target in targets:
                target.set_intensity(0)

    def _get_frequency(self):
        return self._frequency

    def _set_frequency(self, frequency):
        self._frequency = frequency
        self.period_duration = 1.0/(2 * self._frequency)

    frequency = property(_get_frequency, _set_frequency)

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
            targets = self.get_targets(targets)
            val = self.envelope.update(show.time_delta)
            for target in targets:
                target.set_intensity(val * target.intensity)


