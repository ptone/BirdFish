import sys

from birdfish import tween
from birdfish.effects import Pulser
from birdfish.input.midi import MidiDispatcher
from birdfish.lights import LightElement, LightShow
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
single = LightElement(
        start_channel=1,
        name="singletest",
        attack_duration=1,
        release_duration=1.5,
        )

# add the light to a network
dmx3.add_element(single)

# the effect is configured by how many times it should pulse per second
# 1 is the default
pulser = Pulser()

# if you wanted to give the pulse a different characteristic
# pulser = Pulser(on_shape=tween.IN_CIRC, off_shape=tween.OUT_CIRC)

# we append the effect to the elements own list of effects
single.effects.append(pulser)

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


