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
            return -1
        time_delta = current_time - self.last_update
        self.last_update = current_time
        return time_delta

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
        # print "intensity %s " % intensity
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, intensity)
        # here intensity is assumed to be full, as HSV to RGB sets RGB values accordingly
        # print "result %s, %s, %s" % (r,g,b)
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
        else:
            intensity = 0
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

    def _off_trigger(self):
        self.trigger_state = 0
        self.last_update = 0
        # if self.bell_mode:
            # TODO does bell apply to chase classes?
            # ignore release in bell mode
            # return

        logger.debug("%s: pulse trigger off" % self.name)
        for e in self.elements:
                # blackout
                e.trigger(0)
        self.center_position = self.last_center = self.start_pos
        self.trigger_intensity = 0
        if self.moveto is not None:
            self.moveto = self.end_pos  # TODO - should this be left at last set?
            self.setup_move()

    def trigger(self, intensity, **kwargs):
        self.setup_move()
        if intensity > 0 and self.trigger_state == 0:  # or note off message
            self.trigger_state = 1
            self.trigger_intensity = intensity
            logger.debug("%s: chase trigger on @ %s" % (self.name, intensity))
        elif intensity == 0 and self.trigger_state and not self.trigger_toggle:
            self._off_trigger()
        elif intensity and self.trigger_state and self.trigger_toggle:
            logger.info("%s: chase trigger toggle off @ %s" % (self.name, intensity))
            self._off_trigger()

    def setup_move(self):
        # TODO need to differentiate between first move - and subsequent moves
        if not self.move_envelope:
            # TODO the tween type needs to be a settable attr on self
            self.move_envelope = EnvelopeSegment(tween=self.move_tween)
            self.center_position = self.start_pos
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

    def update_position(self, show):
        if self.current_moveto != self.moveto:
            self.setup_move()
        if self.moveto is not None and (self.center_position != self.current_moveto):
            time_delta = self.get_time_delta(show.timecode)
            if time_delta < 0:
                return
            # this min max business is because the tween algos will overshoot
            if self.moveto > self.center_position:
                self.center_position = min(self.moveto,
                        self.move_envelope.update(time_delta))
            else:
                self.center_position = max(self.moveto,
                        self.move_envelope.update(time_delta))


    def update(self, show):
        if not self.trigger_intensity:
            return
        self.update_position(show)
        self.render()
        for effect in self.effects:
            effect.update(show, [self])

    def render(self):
        # TODO needs to handle reverse situations better
        if self.last_center is None:
            self.last_center = self.start_pos
        current_center = int(self.center_position)
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



class EnvelopeElement(LightElement):
    """
    updates a basic envelope object with a change in timeline
    """
    def __init__(self, *args, **kwargs):
        super(EnvelopeElement, self).__init__(*args, **kwargs)
        self.envelope = kwargs.get('envelope', None)
        self.value = 0

    def update(self, show):
        if not self.envelope:
            return
        time_delta = self.get_time_delta(show.timecode)
        if time_delta < 0:
            return
        self.value = self.envelope.update(time_delta)

# @@ EffectChase
# an subclass of chase that moves an effect(s) along a set of elements
#  should have a way of keeping a list of transient
    # or completable effects in a stack, and clear them out when done.

# @@ Need a ChaseGenerator/Manager/Coordinator
# would create a chase, potentially varying some parameters (ie start and end
# or duration) and would trigger it regularly or randomly.  can be used to
# create regular water drips, or drifting snow effects

# @@ Marquee class (sub of LightChase)
"""
has width and gap and speed/rate attribute
each cycle a group of leaders is established and on_action (default trigger)
is performed:
    while running:
    for offset in range(0,(width+gap)):
        for leader in range(start+offset,end,width+gap):
            leader_on(self.elements[leader]) # this would default to trigger, but subclass could customize
            trailer = leader-width
            trailer_off(self.elements[trailer])
    # when offset resets, the last leader, should become trailer of each group

# speed/rate for chase compatability, should speed/time be time for one
# cycle, or for time it would take pulse to move all the way across?

leader_on and trailer_off would be member functions that in default class
would trigger on, trigger off elements - but in subclass could do things like color shift


"""

class LightChaseOldVersion(LightGroup):
    """A chase of light Elements

    speed controls how fast the chase advances from start to finish min speed
    is 0, max_speed is set, then speed control can be mapped to a control
    signal.  @@ have a general problem here with whether to force all map
    values to be 0-255 or allow some to be 0-255 while others can be 0-1

    width defines how many lights are lit up at a time as the chase progresses
    default is 1, the width trails the leading edge.

    a width of 0 means that the element will stay on until the chase itself is
    turned off

    anti-alias: if true, lights will be faded on in proportion to a imaginary
    chase width center moving between discreet elements. In this way, a chase
    can appear to have greater resolution than the number of elements it
    contains.

    a chase can be run under the following trigger modes (chase.trigger_mode):
    sustain - chase runs as long as note/signal/trigger is maintained (default)
    toggle - chase is run continuously after note/signal/trigger until another note/signal/trigger
    single - chase runs through once, no matter how long key held down

    Animation of the chase is one of the following modes (chase.animation_mode):
    loop - chase loops repeating from the beginning when end is reached
    bounce - chase goes from start to end, then reverses from end to start, etc
    marquee - multiple starts are triggered @@need param - perhaps gap between widths

    chase off modes:
    off_trigger
    all off - all lights in chase are turned off at once
    chase off - elements are turned off in sequence
    chase off reverse - elements turned off in reverse sequence
    uses tween_off

    Other paremeters:
    loop_delay - delay between a loop ending, and starting again
    antialias
    randomize - if true, will randomize the order of elements each time through
    element_initialize - a dictionary of parameters to initialize each element
    with

    todo:
    Will need a better way of tracking an index chase that can switch direction.
    the width trail would best be handled by keeping a list of on_elements and
    pushing and popping from that to keep the disired length.

    Need to define a way of a start frame and end frame in addtion to start and
    end that is, the tween values calculated for start and end, but only
    displayed through the frame.  Ultimately means solving a time t for x, so
    that a time offset can be applied to the timedelta passed to the first
    tween update.  This calc could be done at trigger time or init and would
    most practically be done by calling the tween math function in a tight loop
    This only is needed for non-linear tweens, so may not be pressing feature.

    start and end index - defaults to first and last element - but for some tweens, need "margins"

    if duration of elements is short such that all lights are off at end of chase, and off trigger received
        lights will be sent 0 trigger in chase/reverse even though they are out

    Inverse Mode: move a light off - whole chase on, the dark part is what animate (inverse)


    split from middle, or join from ends - this can be done by grouping with 2 chases.
    """

    def __init__(self, *args, **kwargs):
        super(LightChase, self).__init__(*args, **kwargs)
        # @@ pop kwargs elements here
        self.tweener = pytweener.Tweener()
        self.tween_on = "linear"
        self.tween_off = "linear"
        self.start = 0.0
        self.end = float(len(self.elements))
        self.index = 0
        self.speed_control = 1
        self.max_speed = 1
        self.speed = self.speed_control * self.max_speed
        self.animation_mode = "loop"
        self.off_trigger = "all" #all, chase, reverse
        self.running = 0
        self.start_time = 0
        self.antialias = False
        self.width = 1
        self.initialized = False
        self.last_update = 0
        self.triggered_intensity = 0
        self.randomize = False
        self.loop_delay = 0
        self._delay_till = 0 # how loop_delay is implemented
        self.element_initialize = {}
        self._pulse = deque()
        self.last_added_index = 0
        # self.logger = logging.getLogger("%s.%s.%s" % (__name__, "LightChase", self.name))


    def get_tween_mode_func(self, trigger_type="on"):
        if trigger_type.lower() == "on":
            return getattr(self.tweener, self.tween_on.upper())
        else:
            return getattr(self.tweener, self.tween_off.upper())

    def setup(self):
        # @@ is this func needed/used?
        self.index = 0
        self.initialized = True

    def reset(self):
        """reset various values to beginning of chase"""
        pass

    def update(self, show):
        if not self.running: return False
        if self._delay_till:
            if show.timecode < self._delay_till:
                # print "delaying %s < %s" % (show.timecode, self._delay_till)
                return
            else:
                # @@ should these next few lines be factored out into a "reset" func?
                if self.index_tween.complete:
                    self.index_tween.complete = False
                # self.index_tween.delta = self.index = self.start
                self.last_update = 0
                self._delay_till = 0
                self.index_tween.delta = self.index = self.last_added_index = 0
        if not self.last_update:
            self.last_update = show.timecode
            # print "setting start time"
            return False
        time_delta = show.timecode - self.last_update
        self.last_update = show.timecode
        self.tweener.update(time_delta)
        # print "seq index %s" % self.index
        # @@ may need to use math.ciel for intindex when direction is reversed
        intindex = int(self.index)
        if not self.antialias:
            self.index = intindex

        logger.debug("seq index %s" % self.index)


        if self.intensity:
            # this approach to pulse, will handle direction switches easily
            while intindex > self.last_added_index:
                self.last_added_index += 1
                logger.debug("self.last_added_index")
                logger.debug(self.last_added_index)
                index_element = self.elements[self.last_added_index - 1]
                # if self._pulse[-1] != index_element:
                self._pulse.append(index_element)
                index_element.trigger(self.intensity)
            while len(self._pulse) > self._width:
                trail_element = self._pulse.popleft()
                trail_element.trigger(0)

            if self.antialias and (intindex < self.end) and self.index % 1:
                e = self.elements[intindex + 1]
                partial = int((self.index % 1 * 255) * (255 / self.intensity))
                e.trigger(partial)
                # @@ antialias in reverse will be tricky
                # need a direction attribute
                # index of 9.8 in reverse means e[9] is at .2
                # 9.3 is e[9] at .7
                # on top of that, reversed direction could be a leading edge
                # in the case of small width, or retreating edge in case of
                # width = 0.  In latter, want to keep current approach to which
                # side of edge is antialiased
        else:
            # being here means we are animating an off sequence (rev or chase)
            # @@ self.index should be on or off here?
            for e in self.elements[intindex:self.end]:
                e.trigger(self.triggered_intensity)
            for e in self.elements[self.start:intindex]:
                e.trigger(self.intensity)
        # else:
        #            # duration is set - this should be width ulimately @@
        #            print "have duration"
        #            if self.antialias or self.width > 1:
        #                # @@ handle width stuff here
        #
        #                # i, v = divmod (self.index-1, 1)
        #                # self.elements[int(i)].trigger(int(v*255))
        #                if self.index%1 > .5:
        #                    i, v = divmod (self.index+1, 1)
        #                    self.elements[int(i)].trigger(int(v*255)*(255/self.intensity))
        #                self.elements[int(self.index)].trigger(self.intensity)
        #            else:
        #                self.elements[self.index].trigger(self.intensity)

        if self.index == len(self.elements):
            # @@ this needs to be fixed for reverse, bounce, etc
            # @@ also need to test this against endpoint, not len, for chases that overshoot?
            # @@ all this end code should be tied to end of tween duration
            # or perhaps check if index_tween is complete
            logger.debug("end reached")
            if self.randomize:
                random.shuffle(self.elements)

            if self.animation_mode == "loop":
                # reset index
                logger.debug('looping')
                logger.debug(self.loop_delay)
                logger.debug(self._delay_till)
                if self.loop_delay and (self._delay_till == 0):
                    self._delay_till = show.timecode + self.loop_delay
                    return
                logger.debug("loop reset")
                # messing with the tween complete value is a little bit hacky - but we know we
                # can safely do this because we know that nothing will call tweener.update outside of the
                # chase update funciton.
                if self.index_tween.complete:
                    self.logger.debug('resetting tween complete to false')
                    self.index_tween.complete = False
                self.index_tween.delta = self.index = self.last_added_index = 0
                self._delay_till = 0
                # testing:
                self.last_update = 0
            else:
                self.running = self.index = self.last_update = 0

    def kill(self):
        self.running = self.index = self.last_update = self.last_added_index = 0
        self.triggered_intensity = 0
        for e in self.elements:
            e.trigger(0)
            # @@ need a way to keep initialized release intact for final trigger
            if self.element_initialize:
                e.restore_defaults()

        self.tweener.removeTweeningFrom(self)

    def trigger_tween_done(self, *args, **kwargs):
        # @@ will use for looping and passing etc
        # will also use for reset of various values to 0
        self.logger.debug("trigger tween done")
        if self.animation_mode == "loop":
            pass
            # index_tween = self.tweener.getTweensAffectingObject(self)[0]
            # self.start_time = time.time() # @@ could be show time of update, if I had it
        # self.running = 0
        # self.last_update = 0

    def trigger(self, intensity, **kwargs):
        # @@ need to add tween shaping here
        trigger_time = time.time()
        self.logger.debug("len self elements: %s" % len(self.elements))
        if self.trigger_mode == "toggle":
            self.logger.debug("toggle")
            if not intensity:
                # we ignore "note_off" style messages
                return
            if self.triggered_intensity and intensity:
                # trigger on, but already on, so toggle off
                intensity = 0

        if intensity:
            self.logger.debug("trigger on")
            if self.randomize:
                random.shuffle(self.elements)
            self.index = self.start
            self.triggered_intensity = intensity
            # print self.element_initialize
            if not self.end:
                self.end = float(len(self.elements))
            self.logger.debug("self.end: %s" % self.end)
            chase_width = int(self.end - self.start)
            if self.width:
                if self.width > chase_width:
                    raise ValueError("chase width can not be wider than chase")
                self._width = self.width
            else:
                # 0 width implies entire chase range = width
                self._width = chase_width

            tw = self.tweener.addTween(self,
                                    index=self.end,
                                    tweenTime=float(self.speed_control * self.max_speed),
                                    tweenType=self.get_tween_mode_func(),
                                    onCompleteFunction=self.trigger_tween_done,
                                    )
            self.index_tween = tw
            self.running = 1 # 1 is forward, -1 is backwards, 0 is not running
            self.start_time = trigger_time
            for e in self.elements:
                if self.element_initialize:
                    e.set_special_state(self.element_initialize)
                # e.trigger(0) @@ not sure we really want to do this esp if plan is to support overlay more
                # e.trigger(intensity)
        else:
            logger.debug("chase trigger: OFF")
            self.triggered_intensity = 0
            if self.off_trigger == "all" or self.width:
                # a pulse width implies only a "all" off mode
                self.kill()
                return
            elif self.off_trigger == "reverse":
                # @@ assumes only one tween - problematic
                t = self.index_tween
                tweenable = t.getTweenable("index")
                tweenable.startVal = self.index
                tweenable.change = self.index * -1
                t.duration = trigger_time - self.start_time
                t.tween = self.get_tween_mode_func("off")
                self.start_time  = trigger_time
                self.running = -1
            elif self.off_trigger == "chase":
                # just restart the chase with the current zero intensity
                # @@ need to consider how an on or off "bounces" - look at loop - start time reset is not enough
                    # may have any value greater than or lesser than index match intensity?
                self.start_time = trigger_time
                self.index_tween.tween = self.get_tween_mode_func("off")
        self.intensity = intensity


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
