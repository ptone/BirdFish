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
        )

# Define the fireball effect
# this consists of a colorshift that has changes to hue, saturation and intensity
# the use of the OUT_CIRC shape is used to make most of the change happen
# right away, then slowly complete the rest
# the add shift take a start, end, duration, and shape
fireball_duration = 2
fireball = ColorShift()
# we don't want the effect to loop back, so we disable the default looping
fireball.set_loop(None)
# change from yello to red over the duration of the effect
fireball.add_hue_shift(.13, 0, fireball_duration, shape=tween.OUT_CIRC)
# at the beginning, start as white, and in the first 1/8th of the effect
# fade from white to full current hue
fireball.add_saturation_shift(0, 1, fireball_duration/8, shape=tween.OUT_CIRC)
# keep full intensity over the first third of the effect
fireball.add_intensity_shift(1, 1, fireball_duration/3)
# then for the next two thirds, fade out
fireball.add_intensity_shift(1, 0, (fireball_duration/3) * 2, shape=tween.OUT_CIRC)

# add the effect to our single test element
single.effects.append(fireball)

show.add_element(single, network=dmx3)

# now we create a chase of elements, and apply the effect to each element
# the result is that the effect is painted over time
chase = Chase(name='fireball streak')

elementid = 0
for i in range(1, 300, 3):
    elementid += 1
    l = RGBLight(
            start_channel=i,
            name="item_%s" % elementid,
            )
    dmx3.add_element(l)
    chase.elements.append(l)
    # deepcopy is used so that each element has an independent fireball effect
    # over time, if they shared one copy of the effect, then the fade would
    # be synchronized, which is not what we want
    fb = deepcopy(fireball)
    l.effects.append(fb)

chase.end_pos = 70
chase.speed = 3

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
