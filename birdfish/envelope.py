import pytweener
import tween

"""
Notes:
Durations are in seconds
tweener acts on an object and property
tweener updates based on time since last update

core tween consists of  self.delta, tweenable.startValue, tweenable.change, self.duration

One of the challenges extant is how to handle release if full attack has not
been realized yet - duration should not be full duration, but portion remaining
this involves reversing the tween algo to "solve for t" and ff to that time.
could brute force using a time-delta at framerate resolution. - the solution this this
http://en.wikipedia.org/wiki/Bisection_method

Because the tweener acts on obj + property (via a bit of a hack) don't know
if I should perhaps proxy the change here, or point tween directly to object
The latter would be a stronger coupling.

perhaps better to just always work with 0.0 - 1.0

a sustain can be considered a null tween with infinite duration - or basically a
pause at the value at end of decay.

a dumb envelope doesn't know anything about trigger ON/OFF

Should have a way to propogate a single tweened value to many attributes
that could be handled by LightGroup class

an envelope should be an evelope segment - allowing nesting to create complex
envelopes - think a warble on release. Envelope would have to be able to act like
segment (? expose duration, update...)

a pause segment could be represented as a segment with negative duration

"""

class EnvelopeSegment(object):
    """
    contains one phase or segment of a multi-segment envelope
    attributes:
    duration
    shape
    start value
    end value
    end value represented as delta/change
    """

    def __init__(self, tween=tween.LINEAR, start=0, change=1.0, duration=1.0):
        self.tween = tween
        self.start = float(start)
        self.change = float(change)
        self.duration = float(duration)
        assert self.duration > 0  # only a duration > 0 makes sense

    def update(self, delta):
        if delta > self.duration:
            delta = self.duration
        return self.tween(delta, self.start, self.change, self.duration)

    def get_jump_time(self, value):
        return tween.jump_time(self.tween, value, self.start, self.change, self.duration)


class StaticEnvelopeSegment(EnvelopeSegment):
    # just returns the start value unchanged - always
    # will never advance on its own without a trigger interving

    def __init__(self, *args, **kwargs):
        super(StaticEnvelopeSegment, self).__init__(*args, **kwargs)
        self.duration = 0

    def update(self, delta):
        return self.start

class Envelope(EnvelopeSegment):

    def __init__(self, loop=0):
        self.segments = []

        # Not sure I need this state
        self.running = False
        self.paused = 0
        self.pause_duration = 0

        self.loop = loop  # negative loop is infinite looping
        self._duration = None
        self.reset()

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

    def advance(self):
        self.index += 1
        self.current_segment_time_delta = 0
        if self.index + 1 > len(self.segments) and self.loop and self.loop_counter:
            self.index = 0
            if self.loop > 0:  # this is a finite loop
                self.loop_counter -= 1


    def update(self, delta):
        # delta is time passed since last update
        if self.index + 1 > len(self.segments):
            # non looping or end of finite loop
            # just reurn last value until something resets index
            return self.value
        segment = self.segments[self.index]
        self.current_segment_time_delta += delta
        # self.timedelta += delta
        if (segment.duration and
                (self.current_segment_time_delta > segment.duration)):
            overage = self.current_segment_time_delta - segment.duration
            self.advance()
            # TODO don't handle case where overage > new segment
            # duration - could need recursion
            self.current_segment_time_delta = overage
            if self.index + 1 > len(self.segments):
                self.value = segment.update(segment.duration)
            else:
                segment = self.segments[self.index]
                self.value = segment.update(self.current_segment_time_delta)
        else:
            self.value = segment.update(self.current_segment_time_delta)
        return self.value

    @property
    def duration(self):
        if not self._duration:
            self.set_duration()
        return self._duration

    def set_duration(self):
        self._duration = sum([segment.duration for segment in self.segments if segment.duration > 0])


class TriggeredEnvelope(Envelope):

    def __init__(self, *args, **kwargs):
        super(TriggeredEnvelope, self).__init__(*args, **kwargs)
        self.state = 0  # on:1 off:0
        # two states - each has a segment - which may be a envelope with sub-segments

    def trigger(self, state=1, value=1.0):
        """
        state is on or off
        value is 0-1 for max value of tween - currently not
        handled from here - must be set at segment level
        can be used to scale max value on callers end - ie midi velocity
        value of 0 is also implicit state=0
        """
        assert len(self.segments) == 2, "too many segments for a trigger envelope"
        if value == 0:
            state = 0
        if self.state != state:
            self.state = state
            if state:
                # on trigger
                self.reset()
            else:
                # off trigger
                print 'advance'
                self.advance()
                if self.value != self.segments[1].start:
                    self.current_segment_time_delta += self.segments[1].get_jump_time(self.value)
        self.state = state

    def update(self, delta):
        if not (self.state or self.index or self.current_segment_time_delta):
            # not triggered, and at start
            return self.value
        else:
            return super(TriggeredEnvelope, self).update(delta)

class ADSREnvelope(TriggeredEnvelope):
    """
    4 segments ADSR - with S being infinite looping segment
    this is in a two segment triggered state as:
        on-segment envelope:
            attack
            decay
            sustain - StaticEnvelopeSegment
        off:
            release
    """
    def __init__(self, peak_value=1.0, sustain_value=0.8,
            attack_shape=tween.LINEAR, attack_duration=0.5,
            decay_shape=tween.LINEAR, decay_duration=.2,
            release_shape=tween.LINEAR, release_duration=.5,
            bell_mode=False):

        self.attack_envelope = EnvelopeSegment(tween=attack_shape,
                change=peak_value, duration=attack_duration)

        self.on_envelope = Envelope()
        self.on_envelope.segments = [self.attack_envelope]

        decay_change = -(peak_value - sustain_value)
        if decay_change:
            self.decay_envelope = EnvelopeSegment(tween=decay_shape,
                    start=peak_value, change=decay_change, duration=decay_duration)
            self.on_evenlope.segments.append(self.decay_envelope)
        else:
            self.decay_envelope = None

        self.sustain_envelope = StaticEnvelopeSegment(start=sustain_value)
        self.on_envelope.segments.append(self.sustain_envelope)
        self.release_envelope = EnvelopeSegment(tween=release_shape,
                start=sustain_value, change=0-sustain_value, duration=release_duration)
        self.off_envelope = Envelope()
        if self.release_envelope.change and self.release_envelope.duration:
            self.off_envelope.segments.append(self.release_envelope)
        self.segments = [self.on_envelope, self.off_envelope]


class EnvelopeGenerator(object):
    pass



