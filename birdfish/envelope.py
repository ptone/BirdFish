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
        self.start = start
        self.change = change
        self.duration = duration

    def update(self, delta):
        return self.tween(delta, self.start, self.change, self.duration)

class Envelope(EnvelopeSegment):

    def __init__(self):
        self.segments = []
        self.index = 0
        self.value = 0
        self.timedelta # time since start - not sure I need whole time
        self.current_segment_time_delta = 0
        self.tweener = pytweener.Tweener()
        self.running = False
        self.paused = False
        self.pause_duration = 0
        self.loop = 0
        # TODO prob need loops remaining

    def start(self):
        pass

    def stop(self):
        pass

    def pause(self, duration=-1):
        # negative duration is infinite while running
        pass

    def reset(self):
        pass

    def advance(self):
        self.index += 1
        self.current_segment_time_delta = 0

    def update(self, delta):
        # delta is time passed since last update
        segment = self.segments[self.index]
        self.current_segment_time_delta += delta
        if self.current_segment_time_delta >= segment.duration:
            self.value = segment.tween(segment.duration)
            self.advance()
        else:
            self.value = segment.tween(self.current_segment_time_delta)
        return self.value

    @property
    def duration(self):
        return sum([segment.duration for segment in self.segments if segment.duration > 0])


class EnvelopeGenerator(object):
    pass



