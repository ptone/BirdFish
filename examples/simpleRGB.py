import sys
import random

from birdfish.input.midi import MidiDispatcher
from birdfish.lights import RGBLight, LightShow
from birdfish.output.lumos_network import LumosNetwork


# create a light show - manages the updating of all lights
show = LightShow()

# Create a network - in this case, universe 3
dmx3 = LumosNetwork(3)

# add the network to the show
show.networks.append(dmx3)

# create an input interface
dispatcher = MidiDispatcher("MidiKeys")

# create a single RGB light element
single = RGBLight(
        start_channel=10,
        name="singletestb",
        attack_duration=0.5,
        decay_duration=1.5,
        release_duration=0,
        sustain_value=0,
        )
single.hue = random.random()
single.saturation = 1
single.update_rgb()
single.bell_mode = True


# add the light to a network
dmx3.add_element(single)

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

