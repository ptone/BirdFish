import sys
from collections import deque
import colorsys
import threading
# from ola.OlaClient import OlaClient, Universe
# import client_wrapper
import time
# import select
import math
import random
import logging
import pytweener
import tween
from envelope import ADSREnvelope, EnvelopeSegment
from scene import SceneManager
from birdfish.output.base import DefaultNetwork

from birdfish.log_setup import logger

# logger = logging.getLogger('birdfish')
# logger.setLevel(logging.INFO)
# print logger

frame_rate = 30


class BaseLightElement(object):
    """docstring for BaseLightElement"""

    def __init__(self, start_channel=1, *args, **kwargs):
        self.name = kwargs.get('name', "baselight")
        # signal intensity is the value set by the note on velocity -
        # does not reflect current brightness
        self.trigger_intensity = 0.0
        self.intensity = 0.0
        self.channels = {}

        # TODO are these both needed?
        self.last_updated = 0
        self.last_update = 0

        self.channels[start_channel] = 'intensity'

    def update_data(self, data):
        """
        data is an array of data (ie DMX) that should be updated
        with this light's channels
        """
        for channel, value in self.channels.items():
            try:
                # targeted optimization:
                val = self.__dict__[value]
            except AttributeError:
                val = getattr(self, value)
            # TODO current design flaw/limitation
            # using byte arrays instead of float arrays for base
            # data structure - means forcing to bytes here instead
            # of output network level - practically this is OK as all
            # networks are using 1 byte max per channel
            data[channel - 1] = max(data[channel - 1], int(val * 255))

            # no easy way to have more than one light on the same channel would
            # need some way to track which objs have updated a slot - so that
            # each has a shot at increasing it.  @@ need a way to check for
            # channel collisions to avoide unexpected results dmx[channel-1]
            # = max (dmx_val,dmx[channel-1]) #zero index adjust??
            # currently this brightest wins is done by zero out the data

    def get_time_delta(self, current_time):
        if not self.last_update:
            # can't set this from trigger - since don't have access to show
            self.last_update = current_time
            # returning -1 signals that no delta is yet available
            self.time_delta = -1
        self.time_delta = current_time - self.last_update
        self.last_update = current_time
        return self.time_delta

class LightElement(BaseLightElement):

    def __init__(self, *args, **kwargs):
        super(LightElement, self).__init__(*args, **kwargs)
        self.trigger_intensity = 0.0
        self.universe = 1
        self.bell_mode = False
        self.name = kwargs.get("name", "unnamed_LightElement")
        self.adsr_envelope = ADSREnvelope(**kwargs)
        # a simple element has values set externally and does not update
        self.simple = False
        self.trigger_state = 0
        self.trigger_toggle = False
        self.effects = []
        self.pre_update_effects = []

        # self.logger = logging.getLogger(
                # "%s.%s.%s" % (__name__, "LightElement", self.name))

    def bell_reset(self):
        # TODO so why not just trigger 0 here?
        self.trigger_state = 0
        self.last_update = 0
        self.trigger_intensity = 0.0
        self.intensity = 0
        self.adsr_envelope.trigger(state=0)

    def update(self, show):
        if (self.simple or not (self.intensity or self.trigger_intensity)):
            # light is inactive or in sustain mode
            return self.intensity
        time_delta = self.get_time_delta(show.timecode)
        if time_delta < 0:
            # negative means a delta hasn't yet be calculated
            return self.intensity
        if self.bell_mode and self.adsr_envelope.segments[0].index == 2:
            # bell mode ignores trigger off - simulate trigger off once
            # sustain levels are reached
            self.bell_reset()
            return

        if self.adsr_envelope.advancing:
            intensity_scale = self.adsr_envelope.update(time_delta)
            self.set_intensity(self.trigger_intensity * intensity_scale)
        else:
            logger.debug(self.name)
            logger.debug('not advancing, intensity: {}'.format(self.intensity))
            self.trigger_intensity = 0.0
            self.intensity = max(0, self.intensity)
            logger.debug('not advancing, intensity: {}'.format(self.intensity))
            logger.debug('not advancing, trigger intensity: {}'.format(self.trigger_intensity))
            self.last_update = 0
            # only turn off effects here so they can continue to effect releases
            [x.trigger(0) for x in self.effects]

        # moved dmx update to show update, to accomodate effects
        # self.dmx_update(show.universes[self.universe].dmx)
        # if self.last_used_intensity != self.intensity:
        #     print int(self.intensity)
        for effect in self.effects:
            effect.update(show, [self])
        return self.intensity

    def set_intensity(self, intensity):
        # mostly to be overridden by subclasses
        self.intensity = intensity

    def _on_trigger(self):
        pass

    def _off_trigger(self):
        self.trigger_state = 0
        if self.bell_mode:
            # ignore release in bell mode
            return
        logger.debug("%s: trigger off" % self.name)
        self.adsr_envelope.trigger(state=0)
        # note can not set trigger_intensity to 0 here

    def trigger(self, intensity, **kwargs):
        # @@ need toggle mode implementation here
        if self.simple:
            self.intensity = intensity
            return
        if intensity > 0 and self.trigger_state == 0:
            if self.bell_mode:
                self.bell_reset()
            self.trigger_state = 1
            [x.trigger(intensity) for x in self.effects]
            self.trigger_intensity = intensity
            logger.debug("%s: trigger on @ %s" % (self.name, intensity))
            self.intensity = 0.0  # reset light on trigger
            self.adsr_envelope.trigger(state=1)
            self._on_trigger()
        elif intensity == 0 and self.trigger_state and not self.trigger_toggle:
            self._off_trigger()
        elif intensity and self.trigger_state and self.trigger_toggle:
            self._off_trigger()
        elif intensity > self.intensity and self.trigger_state == 1:
            # a greater trigger intensity has occured - override
            self.trigger_intensity = intensity
            logger.debug("%s: override trigger on @ %s" % (self.name, intensity))
            self.intensity = 0.0  # reset light on trigger
            # reset the envelope
            self.adsr_envelope.state = 0
            self.adsr_envelope.trigger(state=1)
        # else redundant trigger


    def off(self):
        """convenience for off"""
        self.trigger(0.0)


class RGBLight(LightElement):
    RED = (1, 0, 0)
    GREEEN = (0, 1, 0)
    BLUE = (0, 0, 1)

    def __init__(self, *args, **kwargs):
        super(RGBLight, self).__init__(*args, **kwargs)
        # need to add in the self.channels[start_channel+n] = 'red'
        start_channel = kwargs.get('start_channel', 1)
        self.red = 0
        self.green = 0
        self.blue = 0
        self._hue = 0.0
        self._saturation = 0
        self.channels[start_channel] = 'red'
        self.channels[start_channel + 1] = 'green'
        self.channels[start_channel + 2] = 'blue'
        # set up rgb values

    def set_intensity(self, intensity):
        self.intensity = intensity
        self.update_rgb()

    def update(self, show):
        return_value = super(RGBLight, self).update(show)
        # TODO - this funciton needed when tweening hue - but can't be used
        # tweening RGB directly
        # self.update_rgb()
        return return_value

    # @@ need to address the attribute of intensity in the context of RGB
    def update_hue(self):
        """updates hue property from RGB values, RGB is always updated when hue changed"""
        adjusted_rgb = [x * self.intensity for x in [
            self.red, self.green, self.blue]]
        h, s, v = colorsys.rgb_to_hsv(*tuple(adjusted_rgb))
        self._hue = h
        self._saturation = s

    def update_rgb(self):
        hue = self._hue
        saturation = self._saturation
        if 'intensity' in self.channels.values():
            # if the fixture has its own intensity slider - always calc RGB values at full intensity
            intensity = 1.0
        else:
            intensity = self.intensity
        # this funct takes all 0-1 values
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, intensity)
        # here intensity is assumed to be full, as HSV to RGB sets RGB values accordingly
        self.red = r
        self.green = g
        self.blue = b

    def _get_hue(self):
        # @@ need to update with function in case r,g,b were updated other than through hue
        return self._hue

    def _set_hue(self, hue):
        self._hue = hue
        self.update_rgb()

    def _get_saturation(self):
        return self._saturation

    def _set_saturation(self, saturation):
        self._saturation = saturation
        self.update_rgb()
        # @@ concept of intensity should be converted to raw RGB for base RGB light
        # no assumption of 4th channel

    hue = property(_get_hue, _set_hue)
    saturation = property(_get_saturation, _set_saturation)

class LightGroup(LightElement):  # TODO why base light element, and not light element?
    """A collection of light Elements triggered in collectively in some form"""
    def __init__(self, *args, **kwargs):
        super(LightGroup, self).__init__(*args, **kwargs)
        self.elements = []
        self.name = kwargs.get("name", "lightgroup")
        self.trigger_mode = kwargs.get("trigger_mode", "sustain")
        e = kwargs.get("elements", [])
        if e:
            # make a copy of the values
            self.elements = list(e)
        self.intensity_overide = 0
        self.intensity = 1.0
        # logger = logging.getLogger("%s.%s.%s" % (__name__, "LightGroup", self.name))
        self.trigger_state = 0  # TODO ie this could go away if this was subclassed differently

    # @@ problematic - problems with __init__ in base classes:
    # def __setattr__(self,key,val):
    #     local_keys = ['name','intensity_overide','element_initialize','elements']
    #     if key in local_keys:
    #         self.__dict__[key] = val
    #     else:
    #         for l in self.elements:
    #             setattr(l,key,val)

    def trigger(self, sig_intensity, **kwargs):
        if sig_intensity:
            intensity = self.intensity_overide or sig_intensity
            [x.trigger(intensity) for x in self.effects]
        else:
            intensity = 0
            [x.trigger(0) for x in self.effects]
        for l in self.elements:
            l.trigger(intensity)

    def set_intensity(self, intensity):
        # the group element always has a pseudo-intensity of 1
        [e.set_intensity(e.intensity * intensity) for e in self.elements]


class Chase(LightGroup):
    def __init__(self,
            # group=None,
            **kwargs):

        super(Chase, self).__init__(**kwargs)
        # self.group = group
        self.center_position = 0
        self.moveto = None
        self.current_moveto = None
        self.speed_mode = 'duration' # or 'speed' of units per second
        self.speed = kwargs.get('speed', 1)
        self.move_envelope = None
        self.move_tween = kwargs.get('move_tween', tween.LINEAR)
        self.start_pos = kwargs.get('start_pos', 0)
        self.end_pos = kwargs.get('end_pos', 10)
        self.moveto = self.end_pos
        self.last_center = None
        self.moving = False
        # off mode may be all, follow, reverse
        self.off_mode = "all"

    def _off_trigger(self):
        self.trigger_state = 0
        self.trigger_intensity = 0
        self.last_update = 0
        # if self.bell_mode:
            # TODO does bell apply to chase classes?
            # ignore release in bell mode
            # return

        logger.debug("%s: pulse trigger off" % self.name)
        self.reset_positions()
        self.setup_move()

        if self.off_mode == "all":
            self.moving = False
            for e in self.elements:
                    # blackout
                    e.trigger(0)
        elif self.off_mode in ["follow", "reverse"]:
            # reset the chase to follow itself as trigger off
            # TODO - placeholder, not sure anything needs to be done
            self.moving = True

    def trigger(self, intensity, **kwargs):
        if intensity > 0 and self.trigger_state == 0:  # or note off message
            if self.moving:
                # we are already in either in an active on or off chase
                # TODO - do we reset everything - draw on top...?
                # print "Already moving"
                return
            self.setup_move()
            self.trigger_state = 1
            self.trigger_intensity = intensity
            self.center_position = self.last_center = self.start_pos
            logger.debug("%s: chase trigger on @ %s" % (self.name, intensity))
            self.moving = True
        elif intensity == 0 and self.trigger_state and not self.trigger_toggle:
            self._off_trigger()
        elif intensity and self.trigger_state and self.trigger_toggle:
            logger.info("%s: chase trigger toggle off @ %s" % (self.name, intensity))
            self._off_trigger()

    def setup_move(self):
        """
        Sets up the move envelope from the current position
        """
        # TODO need to differentiate between first move - and subsequent moves
        if not self.move_envelope:
            # TODO the tween type needs to be a settable attr on self
            self.move_envelope = EnvelopeSegment(tween=self.move_tween)
            self.last_center = self.center_position = self.start_pos

        self.move_envelope.profile.change = self.moveto - self.center_position
        self.move_envelope.profile.start = self.center_position
        if self.speed_mode == 'duration':
            self.move_envelope.profile.duration = self.speed
        elif self.speed_mode == 'speed':
            self.move_envelope.profile.duration = (
                    # ie moving 9 spaces, at 3 spaces per sec = 3 sec
                    self.move_envelope.profile.change / self.speed)
        self.move_envelope.reset()
        self.current_moveto = self.moveto

    def reset_positions(self):
        if (self.off_mode == "reverse"):
            if self.center_position == self.start_pos:
                self.moveto = self.end_pos
            else:
                self.moveto = self.start_pos
        else: # all or follow
            if self.trigger_state:
                self.moveto = int(self.center_position) #  self.end_pos
            else:
                self.moveto = self.end_pos
            self.center_position = self.last_center = self.start_pos
        self.moveto = int(self.moveto)
        self.moving = False

    def update_position(self, show):
        if self.current_moveto != self.moveto:
            self.setup_move()
        if self.moveto is not None and (self.center_position != self.current_moveto):
            # this min max business is because the tween algos will overshoot
            # TODO there is a glitch in the pulse demo where it struggles to
            # get to the very end
            new_position = self.move_envelope.update(self.time_delta)
            if self.moveto > self.center_position:
                self.center_position = min(self.moveto, new_position)
            else:
                self.center_position = max(self.moveto, new_position)
        if self.move_envelope.completed:
            self.reset_positions()

    def update(self, show):

        # always keep time delta updated
        time_delta = self.get_time_delta(show.timecode)
        if self.time_delta < 0:
            return
        if not self.trigger_intensity:
            if self.off_mode == "all":
                return
        if self.moving:
            self.update_position(show)
        self.render()
        for effect in self.effects:
            effect.update(show, [self])

    def render(self):
        # TODO needs to handle reverse situations better
        if self.last_center is None:
            self.last_center = self.start_pos
        current_center = int(self.center_position)
        # trigger everything up to current center
        if not self.trigger_state and self.off_mode == "reverse":
            [e.trigger(self.trigger_intensity) for e in self.elements[current_center:self.last_center]]
        else:
            [e.trigger(self.trigger_intensity) for e in self.elements[self.last_center:current_center]]
        # self.elements[int(self.center_position)].trigger(self.trigger_intensity)
        self.last_center = current_center


class Pulse(Chase):
    """
    a cylon like moving pulse

    center is always full on, and 0 width
    width will then be node-node width
    if width 3 - third node would be off when pulse squarely centered on a node
    width == duration for tweens
    change is always 0 to 1
    """
    def __init__(self,
            # group=None,
            # TODO call super and add pulse specific kwargs extraction
            # TODO once the kwargs settle down - make them explicit
            left_width=3,
            left_shape=tween.LINEAR,
            right_width=3,
            right_shape=tween.LINEAR,
            **kwargs):

        super(Pulse, self).__init__(**kwargs)
        # self.group = group
        self.left_width = left_width
        self.left_shape = left_shape
        self.right_width = right_width
        self.right_shape = right_shape
        self.nodes = []  # a list of element values for pulse
        self.node_range = []  # index range of current pulse

    def set_current_nodes(self):
        node_offset = self.center_position % 1
        left_of_center = math.floor(self.center_position)
        far_left = int(left_of_center - self.left_width)
        self.nodes = []
        for n in range(self.left_width + 1):
            self.nodes.append(
                    # max(0.0, self.left_shape(n + node_offset, 1, -1, self.left_width + 1.0)))
                    self.left_shape(n + node_offset, 1, -1, self.left_width + 1.0))
        if far_left >= 1:
            self.nodes.append(0)
            far_left -= 1
        self.nodes.reverse()
        for n in range(1, self.right_width + 1):
            self.nodes.append(
                    # max(0.0, self.right_shape(max(0, n - node_offset), 1, -1, self.right_width + 1.0)))
                    self.right_shape(max(0, n - node_offset), 1, -1, self.right_width + 1.0))
        self.nodes.append(0)
        self.node_range = range(far_left, far_left + len(self.nodes))
        logger.debug("NodeData:")
        logger.debug(self.node_range)
        logger.debug(self.nodes)

    def update(self, show):
        super(Pulse, self).update(show)
        logger.debug("%s Centered @ %s -> %s" % (self.name, self.center_position, self.end_pos))
        # pong mode:
        if self.center_position == self.end_pos:
            logger.info("%s pong-end @ %s" % (self.name, self.end_pos))
            self.moveto = self.start_pos
            # lw = self.left_width
            # self.left_width = self.right_width
            # self.right_width = lw
        if self.center_position == self.start_pos:
            self.moveto = self.end_pos
            # rw = self.right_width
            # self.right_width = self.left_width
            # self.left_width = rw


    def render(self):
        # if not self.nodes:
            # self.set_current_nodes()
        # TODO why not just iterate over nodes?
        self.set_current_nodes()
        self.elements[max(0, self.node_range[0] - 1)].trigger(0)
        self.elements[min(len(self.elements) - 1, self.node_range[-1] + 1)].trigger(0)
        for i, e in enumerate(self.elements):
            e.trigger(0)
            if i in self.node_range:
                # print i
                # TODO problem here with a moving pulse:
                #   how does the element handle multiple on triggers
                # the trigger 0 is needed otherwise the leading edge just stays
                # dim
                e.trigger(self.nodes[i - self.node_range[0]])

# @@ EffectChase
# an subclass of chase that moves an effect(s) along a set of elements
#  should have a way of keeping a list of transient
    # or completable effects in a stack, and clear them out when done.

# @@ Need a ChaseGenerator/Manager/Coordinator
# would create a chase, potentially varying some parameters (ie start and end
# or duration) and would trigger it regularly or randomly.  can be used to
# create regular water drips, or drifting snow effects

class LightShow(object):

    def send_viewer_data(self):
        dd = ''.join([chr(int(i)) for i in self.networks[1].data])
        f = open('/tmp/dmxpipe', 'wb', 0)
        pad_dd = dd.ljust(512, '\x00')
        f.write(pad_dd)
        f.close()

    def __init__(self):
        super(LightShow, self).__init__()
        self.networks = []
        self.effects = []
        self.frame_rate = 40
        self.dmx_keep_alive = True
        self.scenemanager = SceneManager()
        self.frame_delay = 1.0 / self.frame_rate
        self.running = True
        self.preview_enabled = False
        self.named_elements = {}
        self.default_network = DefaultNetwork()
        self.networks.append(self.default_network)

    def add_element(self, element, network=None):
        if network:
            network.add_element(element)
            if network not in self.networks:
                return self.networks.append(network)
        else:
            return self.default_network.add_element(element)

    def blackout(self):
        for n in self.networks:
            for e in n.elements:
                e.trigger(0)
                if hasattr(e, 'intensity'):
                    e.intensity = 0

    def get_named_element(self, name):
        if name in self.named_elements:
            # a simple cache
            return self.named_elements[name]
        for network in self.networks:
            named_light = network.get_named_element(name)
            if named_light:
                self.named_elements[name] = named_light
                return named_light
        return False

    def init_show(self):
        for n in self.networks:
            n.init_data()
        self.frame_delay = 1.0 / self.frame_rate

    def run_live(self):
        self.init_show()
        self.show_start = time.time()
        self.timecode = self.show_start
        while self.running:
            self.update()
            # print self.time_delta
            # @@ warning if time_delta greater than should be for frame rate
            if (self.time_delta - self.frame_delay) > .01:
                # print "slow by %s" % (self.frame_delay - self.time_delta)
                pass
            time.sleep(self.frame_delay)

    def update(self):
        """The main show update command"""
        now = time.time()
        timecode = now - self.show_start
        self.time_delta = timecode - self.timecode
        self.timecode = timecode
        self.scenemanager.update(self)
        for n in self.networks:
            n.update(self)
        for e in self.effects:
            e.update(self)
        for n in self.networks:
            n.send_data()

        if self.preview_enabled:
            self.send_viewer_data()
