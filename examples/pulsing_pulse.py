import sys

from birdfish.effects import Pulser
from birdfish.input.midi import MidiDispatcher
from birdfish.lights import RGBLight, Pulse, LightShow
from birdfish.output.lumos_network import LumosNetwork
from birdfish import tween


# create a light show - manages the updating of all lights
show = LightShow()

# Create a network - in this case, universe 3
dmx3 = LumosNetwork(3)

# add the network to the show
show.networks.append(dmx3)

# create an input interface
dispatcher = MidiDispatcher("MidiKeys")


p = Pulse(name="greenpulse",
        start_pos=12,
        end_pos=65,
        speed=3,
        move_tween=tween.IN_OUT_CUBIC,
        )

elementid = 0
for i in range(1,360,3):
    elementid += 1
    l = RGBLight(
            start_channel=i,
            name="pulse_%s" % elementid,
            attack_duration=0,
            release_duration=0,
            sustain_value=1,
            )
    # l.hue = random.random() * 255
    l.hue = .74
    l.saturation = 1
    l.update_rgb()
    # l.simple = True
    # add the light to the network
    dmx3.add_element(l)
    p.elements.append(l)


p.start_pos = 12
# p.left_width = p.right_width = 10
p.left_width = 10
p.right_width = 10
p.left_shape = p.right_shape = tween.OUT_CIRC
p.speed = 3
p.moveto = p.end_pos = 65
p.trigger_toggle = True

show.add_element(p)

# BIG FAT TODO - need a way to link the trigger of the group to the trigger of 
# the effect - or is that just handled at the dispatching step? Would be easier
# if there was an add_observers method on dispatcher
pulser = Pulser(triggered=False)
show.effects.append(pulser)
pulser.targets.append(p)

# set the input interface to trigger the element
# midi code 70 is the "J" key on the qwerty keyboard for the midikeys app
dispatcher.add_observer((0,70),p)

# sys.exit(0)
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


