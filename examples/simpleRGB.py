import sys
import random

from birdfish.input.midi import MidiDispatcher
from birdfish.input.osc import OSCDispatcher
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
osc_dispatcher = OSCDispatcher(('0.0.0.0', 8998))

# create a single RGB light element
single = RGBLight(
        start_channel=10,
        name="singletestb",
        attack_duration=0,
        decay_duration=0,
        release_duration=.75,
        sustain_value=1,
        )
single.hue = random.random()
single.saturation = 1
single.update_rgb()
single.bell_mode = True

oscsingle = RGBLight(
        start_channel=91,
        name="singletestb",
        attack_duration=0,
        decay_duration=0,
        release_duration=.75,
        sustain_value=1,
        )

oscsingle.hue = random.random()
oscsingle.saturation = 1
oscsingle.update_rgb()


# add the light to a network
show.add_element(single, network=dmx3)
show.add_element(oscsingle, network=dmx3)

# set the input interface to trigger the element
# midi code 41 is the "Q" key on the qwerty keyboard for the midikeys app
dispatcher.add_observer((0, 41),single)
osc_dispatcher.add_trigger('/2/toggle2', oscsingle)
osc_dispatcher.add_map('/2/fader2', oscsingle, 'hue')
osc_dispatcher.add_map('/elements/fader1', oscsingle, 'saturation', in_range=(0,4))

# startup the midi communication - runs in its own thread
dispatcher.start()
osc_dispatcher.start()

# start the show in a try block so that we can catch ^C and stop the midi
# dispatcher thread
try:
    show.run_live()
except KeyboardInterrupt:
    # cleanup
    dispatcher.stop()
    osc_dispatcher.stop()
    sys.exit(0)

