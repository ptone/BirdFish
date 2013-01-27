import sys

from birdfish.input.midi import MidiDispatcher
from birdfish.input.osc import OSCDispatcher
from birdfish.lights import LightElement, LightShow
from birdfish.output.lumos_network import LumosNetwork


# create a light show - manages the updating of all lights
show = LightShow()

# Create a network - in this case, universe 3
dmx3 = LumosNetwork(3)

# add the network to the show
show.networks.append(dmx3)

# create an input interface
midi_dispatcher = MidiDispatcher("MidiKeys")
osc_dispatcher = OSCDispatcher(('0.0.0.0', 8998))



# create a single channel light element
single = LightElement(
        start_channel=1,
        name="singletest",
        attack_duration=1,
        release_duration=1.5,
        )

# add the light to a network
dmx3.add_element(single)

# set the input interface to trigger the element
# midi code 41 is the "Q" key on the qwerty keyboard for the midikeys app
midi_dispatcher.add_observer((0,41), single)
osc_dispatcher.add_trigger('/elements/push2', single)

# startup the midi communication - runs in its own thread
midi_dispatcher.start()
osc_dispatcher.start()
# start the show in a try block so that we can catch ^C and stop the midi
# dispatcher thread
try:
    show.run_live()
except KeyboardInterrupt:
    # cleanup
    midi_dispatcher.stop()
    osc_dispatcher.stop()
    sys.exit(0)

