from birdfish import envelope

def test_envelope_segment():
    e = envelope.EnvelopeSegment(start=0, change=1.0, duration=1.0)
    r = e.update(.5)
    assert r == .5

def test_envelope_setment_infinite():
    e = envelope.StaticEnvelopeSegment(start=.3)
    r = e.update(.5)
    assert r == .3
    r = e.update(5000)
    assert r == .3

def test_simple_evelope():
    s1 = envelope.EnvelopeSegment(start=0, change=1.0, duration=1.0)
    s2 = envelope.EnvelopeSegment(start=1, change=-1.0, duration=1.0)
    e = envelope.Envelope()
    e.segments = [s1, s2]
    assert e.value == 0
    val = e.update(.5)
    assert val == .5
    val = e.update(.4)
    assert val == .9
    val = e.update(.11)
    assert e.index == 1
    assert val == .99
    val = e.update(.19)
    assert val == .8
    val = e.update(.8)
    assert val == 0
    # the envelope is over, return final value
    val = e.update(3)
    assert val == 0
    # resetting the envelope allows new updates
    e.reset()
    val = e.update(.8)
    assert val == .8

def test_looping_envelope():
    s1 = envelope.EnvelopeSegment(start=0, change=1.0, duration=1.0)
    s2 = envelope.EnvelopeSegment(start=1, change=-1.0, duration=1.0)
    e = envelope.Envelope(loop=2)
    e.segments = [s1, s2]
    # start off with 2 loops remaining
    assert e.loop_counter == 2
    for i in range(6):
        e.update(.5)
    # after 3 seconds - should be in second loop
    assert e.loop_counter == 1
    # after a bunch more time, loop is over, returning last value
    for i in range(10):
        val = e.update(.5)
    assert e.loop_counter == 0
    assert val == 0
    e.loop = -1 # infinite loop
    e.reset()
    for i in range(51):
        val = e.update(.5)
    assert e.loop_counter == -1
    assert val == .5

def test_trigger_envelope():
    s1 = envelope.StaticEnvelopeSegment(start=.3)
    s2 = envelope.EnvelopeSegment(start=.3, change=-.3, duration=1.0)
    e = envelope.TriggeredEnvelope()
    e.segments = [s1, s2]
    # value does not update until triggered
    val = e.update(.5)
    assert val == 0
    e.trigger(state=1)
    val = e.update(.5)
    assert val == .3
    # in this case have static envelope
    for i in range(10):
        val = e.update(.5)
    assert e.index == 0
    assert val == .3
    assert e.state == 1
    e.trigger(state=0)
    assert e.index == 1
    val = e.update(.5)
    assert val == .15
    # non-looping
    for i in range(10):
        val = e.update(.5)
    assert val == 0
    assert e.index == 2
    e.trigger(state=1)
    assert e.index == 0
    # force state of partial value
    e.value = .2
    e.trigger(state=0)
    # test that off segment shortcutted in time to current
    # value
    assert round(e.current_segment_time_delta, 2) == .33


