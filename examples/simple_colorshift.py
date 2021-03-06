import sys

from birdfish import tween
from birdfish.effects import ColorShift
from birdfish.input.midi import MidiDispatcher
from birdfish.lights import LightElement, LightShow, RGBLight
from birdfish.output.lumos_network import LumosNetwork

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

# create a single channel light element
single = RGBLight(
        start_channel=1,
        name="singletest",
        attack_duration=1,
        sustain_value=1,
        release_duration=1.5,
        )

single.saturation = 1

# add the light to a network
show.add_element(single, network=dmx3)

cshift = ColorShift()
cshift.add_hue_shift(start=.5, end=.7, duration=4)
cshift.add_hue_shift(start=.7, end=.1, duration=1)
cshift.add_hue_shift(start=.1, end=.5, duration=2)
cshift.add_sat_shift(start=1, end=0, duration=3.5)
cshift.add_sat_shift(start=0, end=1, duration=3.5)
# the effect is configured by how many times it should pulse per second
# 1 is the default

# if you wanted to give the pulse a different characteristic
# pulser = Pulser(on_shape=tween.IN_CIRC, off_shape=tween.OUT_CIRC)

# we append the effect to the elements own list of effects
single.effects.append(cshift)

# set the input interface to trigger the element
# midi code 41 is the "Q" key on the qwerty keyboard for the midikeys app
dispatcher.add_observer((0,41), single)

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


