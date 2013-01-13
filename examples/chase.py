import sys

from birdfish.input.midi import MidiDispatcher
from birdfish.lights import RGBLight, Chase, LightShow
from birdfish.output.lumos_network import LumosNetwork

# create a light show - manages the updating of all lights
show = LightShow()

# Create a network - in this case, universe 3
dmx3 = LumosNetwork(3)

# add the network to the show
show.networks.append(dmx3)

# create an input interface
dispatcher = MidiDispatcher("MidiKeys")


p = Chase(name="greenpulse")
elementid = 0
for i in range(1,360,3):
    elementid += 1
    l = RGBLight(
            start_channel=i,
            name="pulse_%s" % elementid,
            attack_duration=.3,
            decay_duration=.4,
            release_duration=0,
            sustain_value=0,
            )
    l.hue = .54
    l.saturation = 1
    l.update_rgb()
    l.bell_mode = True
    # l.simple = True
    # add the light to the network
    dmx3.add_element(l)
    p.elements.append(l)


p.start_pos = 12
# p.left_width = p.right_width = 10
p.speed = 1
p.moveto = p.end_pos = 65

show.add_element(p)
# set the input interface to trigger the element
# midi code 70 is the "J" key on the qwerty keyboard for the midikeys app
dispatcher.add_observer((0,70), p)

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


