from __future__ import division

from copy import deepcopy
import sys

from birdfish import colors
from birdfish.effects import ColorShift
from birdfish.input.midi import MidiDispatcher
from birdfish.lights import RGBLight, LightShow, Chase
from birdfish.output.lumos_network import LumosNetwork
from birdfish import tween

# from birdfish.log_setup import logger
# logger.setLevel(10)

# create a light show - manages the updating of all lights
show = LightShow()

# Create a network - in this case, universe 3
dmx3 = LumosNetwork(3)

# add the network to the show
show.networks.append(dmx3)

# create an input interface
dispatcher = MidiDispatcher("MidiKeys")
# osc_dispatcher = OSCDispatcher(('0.0.0.0', 8998))

# create a single RGB light element
single = RGBLight(
        start_channel=61,
        name="singletestb",
        attack_duration=0,
        decay_duration=0,
        release_duration=0,
        sustain_value=1,
        )
single.hue = colors.RED
single.saturation = 1
single.update_rgb()

# Define the fireball effect
# this consists of a colorshift that has changes to hue, saturation and intensity
fireball_duration = 2
fireball = ColorShift()
fireball.set_loop(None)
fireball.add_hue_shift(.13, 0, fireball_duration, shape=tween.OUT_CIRC)
fireball.add_saturation_shift(0, 1, fireball_duration/8, shape=tween.OUT_CIRC)
fireball.add_intensity_shift(1, 1, fireball_duration/3)
fireball.add_intensity_shift(1, 0, (fireball_duration/3) * 2, shape=tween.OUT_CIRC)

single.effects.append(fireball)

show.add_element(single, network=dmx3)

chase = Chase(name='fireball streak')

elementid = 0
for i in range(1, 300, 3):
    elementid += 1
    l = RGBLight(
            start_channel=i,
            name="item_%s" % elementid,
            attack_duration=0,
            decay_duration=0,
            release_duration=0,
            sustain_value=1,
            )
    dmx3.add_element(l)
    chase.elements.append(l)
    # deepcopy is used so that each element has an independent fireball effect
    # over time
    fb = deepcopy(fireball)
    l.effects.append(fb)
    # l.effects.append(fireball)


chase.end_pos = 70
print chase.moveto
chase.speed = 3
print chase.speed
# add the light to a network
show.add_element(chase)

# set the input interface to trigger the element
# midi code 41 is the "Q" key on the qwerty keyboard for the midikeys app
dispatcher.add_observer((0, 41), single)  #Q
dispatcher.add_observer((0, 70), chase)  #J

# startup the midi communication - runs in its own thread
dispatcher.start()

# start the show in a try block so that we can catch ^C and stop the midi
# dispatcher thread
try:
    show.run_live()
except KeyboardInterrupt:
    # cleanup
    dispatcher.stop()
    sys.exit(0)
