import sys

from birdfish.effects import Blink
from birdfish.input.midi import MidiDispatcher
from birdfish.lights import LightElement, LightShow
from birdfish.output.lumos_network import LumosNetwork


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
show.add_element(single, network=dmx3)

# a blinker is configured by how many times it should blink per second
# 2 is the default
blinker = Blink(frequency=3)

# we tell the blinker what elements it should effect
blinker.targets.append(single)

# we add the blinker to the shows effects
show.effects.append(blinker)

# set the input interface to trigger the element
# midi code 41 is the "Q" key on the qwerty keyboard for the midikeys app
dispatcher.add_observer((0,41),single)

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


