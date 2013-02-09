
import sys

from birdfish.input.midi import MidiDispatcher
from birdfish.lights import RGBLight, Chase, LightShow, LightGroup
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

pixels = LightGroup()

elementid = 0
for i in range(1,360,3):
    elementid += 1
    l = RGBLight(
            start_channel=i,
            name="pulse_%s" % elementid,
            attack_duration=0,
            decay_duration=0,
            release_duration=0,
            sustain_value=1,
            )
    l.hue = .96
    l.saturation = 1
    l.update_rgb()
    dmx3.add_element(l)
    pixels.elements.append(l)

doors = LightGroup()

for i in range(10, 80, 10):
    simple = Chase(name="simplechase")
    simple.start_pos = 1
    simple.speed = .5
    simple.moveto = simple.end_pos = 11
    simple.off_mode = "follow"
    simple.elements = pixels.elements[i:i+11]

    show.add_element(simple)
    doors.elements.append(simple)
# set the input interface to trigger the element
# midi code 70 is the "V" key on the qwerty keyboard for the midikeys app
dispatcher.add_observer((0,65), doors)

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
