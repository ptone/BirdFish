import warnings

import tween
from birdfish.log_setup import logger

"""
Implementation of envelopes

An evelope is an object that is responsible for changing some value over time.

Changes are divided into segments.

At the lowest level a segment consists of a EnvelopeProfile representing the
parameters of teh change. The profile consists of:
    Tweening curve function (easing curve)
    start value
    change in value
    duration of change (in seconds)

A profile can be used for one or more EnvelopeSegments. These segments manage
the increment of time and store the value.

An envelope consists of a group of segments, as each segment is completed, the
next segment is run.

Envelopes can act as segments to other envelopes allowing for nested changes.

"""
# TODO
# Need to introduce an EnvelopeProfile for the reusable math bits
# all cumulative update tracking should happen in the end segment
# and a containing envelope needs to "reset" the segment as needed


class EnvelopeProfile(object):
    """
    contains the math core for a segment

    This is factored out from the segment so that one profile can be used
    across multiple segments/envelopes - as envelope instances are ultimately
    tied 1:1 with light elements.
    """

    def __init__(self, tween=tween.LINEAR, start=0, change=1.0, duration=1.0,
            label="profile"):
        self.tween = tween
        self.start = float(start)
        self.change = float(change)
        self.duration = float(duration)
        self.label = label

        # assert self.duration > 0  # only a duration > 0 makes sense

    def get_value(self, delta):
        if delta > self.duration:
            delta = self.duration
        # as this class just provides the math - it does not store a value
        return self.tween(delta, self.start, self.change, self.duration)

    def get_jump_time(self, value):
        return tween.jump_time(self.tween, value, self.start, self.change,
                self.duration)


class EnvelopeSegment(object):
    """
    represents a segment of value change - has a reference to a profile that
    is used for calculations
    """
    def __init__(self, tween=tween.LINEAR, start=0, change=1.0, duration=1.0,
            profile=None, label="segment"):
        if profile:
            self.profile = profile
        else:
            self.profile = EnvelopeProfile(
                    tween=tween,
                    start=start,
                    change=change,
                    duration=duration,
                    label="%s-profile" % label
            )

        self.label = label
        self.elapsed = 0
        self.value = 0

    def __repr__(self):
        return self.label

    def reset(self):
        self.elapsed = 0
        self.value = 0

    def get_profile(self):
        # provide a function that can be used on envelopes or segments to get
        # current profile in effect
        return self.profile

    def get_current_segment(self):
        return self

    @property
    def duration(self):
        return self.profile.duration

    def update(self, delta):
        # show updates are based on a delta since last update
        # while tweens are based on elapsed time
        self.elapsed += delta
        if not self.duration:
            # no duration - instantly get last value
            self.value = self.profile.start + self.profile.change
        else:
            self.value = self.profile.get_value(self.elapsed)
        return self.value

    @property
    def completed(self):
        return self.elapsed >= self.profile.duration


class StaticEnvelopeSegment(EnvelopeSegment):
    # just returns the start value unchanged - always
    # will never advance on its own without a trigger interving

    def __init__(self, *args, **kwargs):
        super(StaticEnvelopeSegment, self).__init__(*args, **kwargs)
        self.profile.duration = 0
        # TODO - this is a hack so sustain doesn't get advanced over
        # as part of an on envelope that has no attack
        # can't use a neg value as flag - as it will mess with duration math
        self.profile.duration = 99999999999999999999999999999999

    def update(self, delta):
        # always return the starting value
        return self.profile.start


class Envelope(EnvelopeSegment):

    def __init__(self, loop=0, label="envelope"):
        self.segments = []
        self.label = label
        self.index = 0
        self.advancing = True

        # Not sure I need this state
        self.running = False
        self.paused = 0
        self.pause_duration = 0

        self.loop = loop  # negative loop is infinite looping
        self._duration = 0
        self.reset()

    @property
    def current_segment(self):
        return self.segments[self.index]

    def add_segment(self,
            start=0,
            change=1,
            end=None,
            duration=1,
            shape=tween.LINEAR):

        if end is not None:
            change = end - start
        seg = EnvelopeSegment(
                start=start,
                change=change,
                duration=duration,
                tween=shape,
                )
        self.segments.append(seg)

    def get_profile(self):
        logger.debug("Envelop %s profile property, index: %s" % (self.label,
            self.index))
        end_segment = self.get_current_segment()
        return end_segment.profile

    def get_current_segment(self):
        return self.segments[self.index].get_current_segment()

    def start(self):
        pass

    def stop(self):
        pass

    def pause(self, duration=-1):
        # negative duration is infinite while running
        pass

    def reset(self):
        self.set_duration()
        self.loop_counter = self.loop
        self.index = 0
        self.value = 0
        self.current_segment_time_delta = 0
        for segment in self.segments:
            segment.reset()
        self.advancing = True

    def advance(self):
        # return True if advanced
        if self.index + 1 == len(self.segments):  # last segment
            if self.loop:
                self.segments[self.index].reset()
                self.index = 0
                self.current_segment_time_delta = 0
                if self.loop_counter and self.loop > 0:
                    # this is a finite loop
                    self.loop_counter -= 1
                return True
            else:
                # non-looping, or done with final loop
                pass
        else:
            # proceed through sequence of segments
            if self.segments[self.index]:
                # TODO - this is a reason to always have a segment of some sort
                # even if it is a null segment, rather than use none
                self.segments[self.index].reset()
            self.index += 1
            self.current_segment_time_delta = 0
            logger.debug("advanced to %s" % self.segments[self.index].label)
            return True
        self.advancing = False
        return False

    def update(self, delta):
        # delta is time passed since last update
        if self.index + 1 > len(self.segments):
            # non looping or end of finite loop
            # just reurn last value until something resets index
            return self.value
        segment = self.current_segment
        if not segment.duration:
            # for example, no attack value
            # self.advance()
            pass
        self.current_segment_time_delta += delta
        logger.debug("%s-%s: self current elapsed %s, after delta %s" % (
                id(self),
                self.label,
                self.current_segment_time_delta,
                delta,
        ))
        logger.debug("current segment %s" % segment.label)
        # TODO this is advancing past end of on segemnt,
        # when that on segment only contains a 0 duration attack, and no decay
        # not going into any sustain
        if (self.current_segment_time_delta > segment.duration and
                not isinstance(segment, StaticEnvelopeSegment)):
            overage = self.current_segment_time_delta - segment.duration
            logger.debug("overage: %s" % overage)
            # TODO currently don't handle case where overage > new segment
            # duration - could need recursion

            if self.advance():
                logger.debug('advanced, new delta: %s' % overage)
                delta = self.current_segment_time_delta = overage
                segment = self.segments[self.index]
            else:
                logger.debug("did not advance after overage")

        self.value = segment.update(delta)
        return self.value

    @property
    def duration(self):
        if not self._duration:
            self.set_duration()
        return self._duration

    def set_duration(self):
        # a duration of 0 means it is infinite
        self._duration = 0
        for segment in self.segments:
            # TODO need to decide if segment can be None, or is always
            # a segment subclass otherwise could just self._duration
            # = sum([segment.duration for segment in self.segments if
            # segment.duration > 0])
            if segment and segment.duration:
                self._duration += segment.duration


class TriggeredEnvelope(Envelope):

    def __init__(self, *args, **kwargs):
        super(TriggeredEnvelope, self).__init__(*args, **kwargs)
        self.state = 0  # on:1 off:0
        self.label = kwargs.get('label', 'triggered-envelope')
        # two states - each has a segment - which may be a envelope with
        # sub-segments

    def trigger(self, state=1, value=1.0, force=False):
        """
        state is on or off
        value is 0-1 for max value of tween - currently not
        handled from here - must be set at segment level
        can be used to scale max value on callers end - ie midi velocity
        value of 0 is also implicit state=0
        """
        assert len(self.segments) == 2, "too many segments for a trigger envelope"
        # TODO I think the whole value arg and associated code needs to go
        # this is only about state
        if value == 0:
            state = 0
        if force:
            self.state = not state
        if self.state != state:
            self.state = state
            if state:
                # on trigger
                logger.debug("envelope trigger on - resetting")
                self.reset()
                logger.debug("%s-%s: self post reset current elapsed %s" % (
                        id(self),
                        self.label,
                        self.current_segment_time_delta,
                        ))
            else:
                # off trigger
                self.advance()
                logger.debug("current value: %s" % self.value)
                logger.debug("current change for release: %s" %
                        self.segments[1].get_profile().change)
                if self.value < self.segments[1].get_profile().start:
                    # TODO this shortcut works on release, but for attack?
                    # also need to sort out when in decay (say .9), and release
                    # start is .8 - now will be greater - want a way to change
                    # release start value for this time only
                    # perhaps start value should always just be current value
                    # - for when greater if dimmer, want shorter release if
                    # brigher (.9) then want standard release time but greater
                    # change

                    jump_value = self.segments[1].get_profile().get_jump_time(
                            self.value)
                    self.update(jump_value)
                # TODO - this won't work for multisegment release
                # if not hasattr(self.segments[1], 'segments'):
                # self.segments[1].segments[0].profile.change = -1 * self.value
                # self.segments[1].segments[0].profile.start = self.value
                # else:
                    # print "has segments"
                    # print self.segments[1].segments

                logger.debug("new current change for release: %s" %
                        self.segments[1].get_profile().change)
        self.state = state

    def update(self, delta):
        if not (self.state or self.index or self.current_segment_time_delta):
            # not triggered, and at start
            return self.value
        else:
            return super(TriggeredEnvelope, self).update(delta)


class ADSREnvelope(TriggeredEnvelope):
    """
    4 segments ADSR - with S being static segment
    this is in a two segment triggered state as:
        on-segment envelope:
            attack
            decay
            sustain (StaticEnvelopeSegment)
        off:
            release
    """
    def __init__(self,
            peak_value=1.0,
            sustain_value=0.8,
            attack_shape=tween.LINEAR,
            attack_duration=0.5,
            decay_shape=tween.LINEAR,
            decay_duration=.2,
            release_shape=tween.LINEAR,
            release_duration=.5,
            bell_mode=False,
            label='ADSR-envelope',
            **kwargs):

        super(ADSREnvelope, self).__init__(loop=0, label=label)
        self.attack_envelope = EnvelopeSegment(
                tween=attack_shape,
                change=peak_value,
                duration=attack_duration,
                label="attack",
                )

        self.on_envelope = Envelope(label="on-envelope")
        self.on_envelope.segments = [self.attack_envelope]

        decay_change = -(peak_value - sustain_value)

        if decay_change:
            self.decay_envelope = EnvelopeSegment(
                    tween=decay_shape,
                    start=peak_value,
                    change=decay_change,
                    duration=decay_duration,
                    label="decay",
                    )
            self.on_envelope.segments.append(self.decay_envelope)
        else:
            self.decay_envelope = None

        self.sustain_envelope = StaticEnvelopeSegment(start=sustain_value,
                label="sustain")
        self.on_envelope.segments.append(self.sustain_envelope)
        self.release_envelope = EnvelopeSegment(
                tween=release_shape,
                start=sustain_value,
                change=0 - sustain_value,
                duration=release_duration,
                label="release",
                )
        self.off_envelope = Envelope(label="off-envelope")
        self.off_envelope.segments.append(self.release_envelope)
        self.segments = [self.on_envelope, self.off_envelope]


class ColorEnvelope(object):
    """
    Manages a set of envelopes in parallel related to color change
    """
    # TODO notes:
    # how does it handle the existing color of an element
    # can I handle explicit start color, or take current color and shift both
    # can we reset the color to the original?
    #
    def __init__(self, **kwargs):
        self.hue_envelope = Envelope(loop=-1)
        self.saturation_envelope = Envelope(loop=-1)
        self.intensity_envelope = Envelope(loop=-1)

    def _add_shift(self, start, end, duration, shape, envelope):
        if envelope is not None:
            change = end - start
            seg = EnvelopeSegment(
                    start=start,
                    change=change,
                    duration=duration,
                    tween=shape,
                    )
            envelope.segments.append(seg)
        else:
            warnings.warn("Envelope disabled")

    def set_loop(self, loop):
        for env in (self.hue_envelope, self.saturation_envelope, self.intensity_envelope):
            env.loop = loop

    def add_hue_shift(self, start=0, end=1, duration=5, shape=tween.LINEAR):
        self._add_shift(start, end, duration, shape, self.hue_envelope)

    def add_saturation_shift(self, start=1, end=1, duration=5, shape=tween.LINEAR):
        self._add_shift(start, end, duration, shape, self.saturation_envelope)

    def add_intensity_shift(self, start=1, end=1, duration=5, shape=tween.LINEAR):
        self._add_shift(start, end, duration, shape, self.intensity_envelope)

    def _color_update(self, time_delta):
        # if any of the shift envelopes have been disabled by being set to None
        # return None for those values
        if self.hue_envelope:
            hue = self.hue_envelope.update(time_delta)
        else:
            hue = None
        if self.saturation_envelope:
            sat = self.saturation_envelope.update(time_delta)
        else:
            sat = None
        if self.intensity_envelope:
            intensity = self.intensity_envelope.update(time_delta)
        else:
            intensity = None
        return (hue, sat, intensity)

    def update(self, time_delta):
        return self._color_update(time_delta)

    def reset(self):
        for env in [self.hue_envelope, self.saturation_envelope, self.intensity_envelope]:
            if env is not None:
                env.reset()

    @property
    def duration(self):
        hue_duration = sat_duration = int_duration = 0
        if self.hue_envelope:
            hue_duration = self.hue_envelope.duration
        if self.saturation_envelope:
            sat_duration = self.saturation_envelope.duration
        if self.intensity_envelope:
            int_duration = self.intensity_envelope.duration
        # TODO should we ensure they are all equal, could result in some
        # funky rendering if one is looping differently - maybe that is not bad
        return max(hue_duration, sat_duration, int_duration)
