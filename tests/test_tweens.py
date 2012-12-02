from birdfish import tween

def test_tween_jump():
    b = 0
    c = 1
    d = 6
    target = .5
    tween_t = tween.LINEAR

    val = tween.jump_time(tween_t, target, b, c, d)
    assert int(val) == 3

