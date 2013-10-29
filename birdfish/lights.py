from __future__ import division

from collections import deque
from copy import deepcopy
import colorsys
import warnings
import time
import math
import random
import tween
from envelope import ADSREnvelope, EnvelopeSegment
# from scene import SceneManager
from birdfish.colors import DIYC_DIM
from birdfish.output.base import DefaultNetwork

from birdfish.log_setup import logger


class PhysicalDevice(object):
    """
    This item represents an element that provides channel data to a network.
    """

    def __init__(self, start_channel=1, *args, **kwargs):
        """
        start_channel: The first channel this device occupies in a
        network.

        The channels dictionary contains a mapping of channel numbers to object
        attributes.
        """
        # signal intensity is the value set by the note on velocity -
        # does not reflect current brightness
        self.channels = {}
        self.intensity = 0
        self.channels[start_channel] = 'intensity'
        self.gamma = None
        self.start_channel = start_channel

    def update_channels(self):
        # apply dimming or other adjustments
        if self.gamma:
            # TODO for now gamma is as an 8 bit lookup
            dmx_val = int(self.intensity * 255)
            val = self.gamma[dmx_val]
            self.intensity = val / 255

    def set_intensity(self, intensity):
        # TODO note this setter may be superfluos
        self.intensity = intensity

    def update_data(self, data):
        """
        This method is called by the network containing this item in order to
        retrieve the current channel values.

        Data is an array of data (ie DMX) that should be updated
        with this light's channels
        """
        self.update_channels()
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
            # Here the channel values are highest value wins
            data[channel - 1] = max(data[channel - 1], int(val * 255))


class RGBDevice(PhysicalDevice):
    def __init__(self, *args, **kwargs):
        super(RGBDevice, self).__init__(*args, **kwargs)
        # need to add in the self.channels[start_channel+n] = 'red'
        self.red = 0
        self.green = 0
        self.blue = 0
        self.channels[self.start_channel] = 'red'
        self.channels[self.start_channel + 1] = 'green'
        self.channels[self.start_channel + 2] = 'blue'
        self.gamma = DIYC_DIM

    def update_channels(self):
        # update RGB only once per cycle here, instead of
        # every hue update
        super(RGBDevice, self).update_channels()


class BaseLightElement(object):
    """
    This class handles trigger events, and is updated with the show timeline.
    """

    # TODO need to factor the ADSR related parts out of this class

    def __init__(self,
            name="unamed_LightElements",
            bell_mode=False,
            simple=False,
            trigger_toggle=False,
            *args, **kwargs):
        """
        name is used for retrieving elements from the show

        bell_mode is a boolean that determines how the element proceeds through
        the Attack-Decay-Sustain-Release envelope in response to triggers. When
        bell_mode is True, the envelope continues through the end of release on
        the "on" trigger alone. When bell_mode is False the ADSR envelope halts
        at sustain, until an off trigger event.

        simple is an attribute, which will disable the update process, allowing
        the elements attributes to be set directly.  This can be useful for
        situations where a parent object manages all the attribute changes for
        child elements.

        trigger_toggle determines the way on and off triggers are handled. When
        True, only 'on' trigger events are responded to, and they toggle the
        element on and off. This can be useful if the device only supports
        momentary push buttons.

        Effects contain an array of :class:`~birdfish.effects.BaseEffect`
        objects.
        """

        self.trigger_intensity = 0.0
        self.bell_mode = bell_mode
        self.name = name
        self.adsr_envelope = ADSREnvelope(**kwargs)
        # a simple element has values set externally and does not update
        self.simple = simple
        self.trigger_state = 0
        self.last_update = -1
        self.trigger_toggle = trigger_toggle
        self.effects = []
        self.pre_update_effects = []
        self._intensity = 0

    def bell_reset(self):
        # TODO is this method still needed?
        self._off_trigger()

    @property
    def update_active(self):
        """
        This property is the API for any class to determine whether updates
        should continue to be passed to this element.
        """
        return self.trigger_intensity

    def update(self, show):
        """
        The update method is called once per iteration of the main show loop.
        """
        if (self.simple or not (self.update_active)):
            # light is inactive or in sustain mode
            return self.intensity
        if self.bell_mode and self.adsr_envelope.segments[0].index == 1:
            # bell mode ignores trigger off - simulate trigger off once
            # sustain levels are reached
            self.bell_reset()
            return

        if self.adsr_envelope.advancing:
            intensity_scale = self.adsr_envelope.update(show.time_delta)
            self.set_intensity(self.trigger_intensity * intensity_scale)
        elif self.trigger_intensity:
            logger.debug(self.name)
            logger.debug('not advancing, intensity: {}'.format(self.intensity))
            self.trigger_intensity = 0.0
            self.intensity = max(0, self.intensity)
            logger.debug('not advancing, intensity: {}'.format(self.intensity))
            logger.debug('not advancing, trigger intensity: {}'.format(
                self.trigger_intensity))
            # only turn off effects here so they can continue to effect
            # releases
            [x.trigger(0) for x in self.effects]

        # moved dmx update to show update, to accomodate effects
        # self.dmx_update(show.universes[self.universe].dmx)
        # if self.last_used_intensity != self.intensity:
        #     print int(self.intensity)
        for effect in self.effects:
            effect.update(show, [self])
        self.device.set_intensity(self.intensity)
        return self.intensity

    def set_intensity(self, intensity):
        # mostly to be overridden by subclasses
        self._intensity = intensity
        if hasattr(self, 'device'):
            self.device.intensity = intensity

    def get_intensity(self):
        return self._intensity

    intensity = property(get_intensity, set_intensity)

    def _on_trigger(self, intensity, **kwargs):
        pass

    def _off_trigger(self):
        self.trigger_state = 0
        logger.debug("%s: trigger off" % self.name)
        self.adsr_envelope.trigger(state=0)
        # note can not set trigger_intensity to 0 here

    def trigger(self, intensity, **kwargs):
        # @@ need toggle mode implementation here
        if self.simple:
            self.set_intensity(intensity)
            return
        if intensity > 0 and self.trigger_state == 0:
            if self.bell_mode:
                self.bell_reset()
            self.trigger_state = 1
            [x.trigger(intensity) for x in self.effects]
            self.trigger_intensity = intensity
            logger.debug("%s: trigger on @ %s" % (self.name, intensity))
            self.set_intensity(0.0)  # reset light on trigger
            self.adsr_envelope.trigger(state=1)
            self._on_trigger(intensity, **kwargs)
        elif intensity == 0 and (self.trigger_state and not self.trigger_toggle
                and not self.bell_mode):
            self._off_trigger()
        elif intensity and self.trigger_state and self.trigger_toggle:
            self._off_trigger()
        elif intensity > self.intensity and self.trigger_state == 1:
            # a greater trigger intensity has occured - override
            self.trigger_intensity = intensity
            logger.debug("%s: override trigger on @ %s" %
                    (self.name, intensity))
            self.intensity = 0.0  # reset light on trigger
            # reset the envelope with a forced on trigger
            self.adsr_envelope.trigger(state=1, force=True)
        # else redundant trigger

    def off(self):
        """convenience for off, synonym for trigger(0)"""
        self.trigger(0)


class LightElement(BaseLightElement, PhysicalDevice):
    """
    This is a composed class that represents a basic light that has both
    behaviors and channel data
    """
    def __init__(self, device_element=None, *args, **kwargs):
        BaseLightElement.__init__(self, *args, **kwargs)
        if not device_element:
            self.device = PhysicalDevice(*args, **kwargs)
        else:
            self.device = device_element


class RGBLight(LightElement):

    def __init__(self, device_element=None, *args, **kwargs):
        BaseLightElement.__init__(self, *args, **kwargs)
        if not device_element:
            self.device = RGBDevice(*args, **kwargs)
        else:
            self.device = device_element
        self._hue = 0.0
        self._saturation = 0
        self.normalize = False

    def update(self, show):
        return_value = super(RGBLight, self).update(show)
        # TODO - this funciton needed when tweening hue - but can't be used
        # tweening RGB directly
        self.update_rgb()
        return return_value

    def update_rgb(self):
        hue = self._hue
        saturation = self._saturation
        if 'intensity' in self.device.channels.values():
            # if the fixture has its own intensity slider - always calc RGB
            # values at full intensity
            intensity = 1.0
        else:
            intensity = self.intensity
        # this funct takes all 0-1 values
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, intensity)
        if self.normalize and any((r, g, b)):
            maxval = max((r, g, b))
            adj = maxval / 1
            r, g, b = colorsys.hsv_to_rgb(hue, saturation, intensity * adj)
        self.red = self.device.red = r
        self.green = self.device.green = g
        self.blue = self.device.blue = b

    # TODO need R, G, B setters - and an update hue mirror
    #

    def _get_hue(self):
        # TODO need to update with function in case r,g,b were updated other
        # than through hue
        return self._hue

    def _set_hue(self, hue):
        self._hue = hue

    def _get_saturation(self):
        return self._saturation

    def _set_saturation(self, saturation):
        self._saturation = saturation
        # TODO concept of intensity should be converted to raw RGB for base RGB
        # light no assumption of 4th channel

    # @@ need to address the attribute of intensity in the context of RGB
    def update_hue(self):
        """
        updates hue property from RGB values, RGB is always updated when hue
        changed
        """
        adjusted_rgb = [x * self.intensity for x in [
            self.red, self.green, self.blue]]
        h, s, v = colorsys.rgb_to_hsv(*tuple(adjusted_rgb))
        self._hue = h
        self._saturation = s

    hue = property(_get_hue, _set_hue)
    saturation = property(_get_saturation, _set_saturation)


class LightGroup(BaseLightElement):
    # TODO why base light element, and not light element?
    """
    A collection of light Elements triggered in collectively in some form
    """
    def __init__(self, *args, **kwargs):
        super(LightGroup, self).__init__(*args, **kwargs)
        self.elements = kwargs.get('elements', [])
        self.name = kwargs.get("name", "lightgroup")
        # TODO need min and max intensity - at a more baseclass level
        self.max_intensity = 1.0

    def trigger(self, sig_intensity, **kwargs):
        if sig_intensity:
            intensity = min(self.max_intensity, sig_intensity)
            self.trigger_state = 1
        else:
            self.trigger_state = 0
            intensity = 0.0
        self.trigger_intensity = intensity
        [l.trigger(intensity) for l in self.elements]
        [x.trigger(intensity) for x in self.effects]

    def set_intensity(self, intensity):
        # the group element always has a pseudo-intensity of 1
        [e.set_intensity(e.intensity * intensity) for e in self.elements]

    @property
    def update_active(self):
        return any([e.update_active for e in self.elements])

    def update(self, show):
        if self.trigger_state or self.update_active:
            for element in self.elements:
                if element.last_update != show.timecode:
                    # avoide updated sub elements twice if they are also in the
                    # main show list of elements
                    element.update(show)
                    element.last_update = show.timecode

            # TODO - setting trigger_intensity here messes up chases
            # but without it need a better way to remove spent spawn
            # self.trigger_intensity = self.update_active

    # TODO could have hue, saturation and other basic property passthrough?


class Chase(LightGroup):
    def __init__(self,
            # group=None,
            **kwargs):

        super(Chase, self).__init__(**kwargs)
        # self.group = group
        self.anti_alias = False
        self.center_position = 0
        self.moveto = None
        self.current_moveto = None
        self.speed_mode = 'duration'  # or 'speed' of units per second
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
        self.continuation_mode = None
        self.move_complete = False
        self.sweep = True
        self.width = 1

    def _off_trigger(self):
        self.trigger_state = 0
        # TODO - setting trigger intensity to 0 here - works for sweeps
        # but non-sweep has to use trigger 1 as it doesn't have access to the
        # original trigger_intensity
        self.trigger_intensity = 0

        # if self.bell_mode:
            # TODO does bell apply to chase classes?
            # ignore release in bell mode
            # return

        logger.debug("%s: pulse trigger off" % self.name)
        self.reset_positions()

        if self.off_mode == "all":
            # TODO some cleanup needed - moving set to false in
            # reset_positions, need to more clearly define between
            # these functions what does what
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
            # self.reset_positions()
            # TODO so reset positions only for off trigger?
            self.trigger_state = 1
            self.trigger_intensity = intensity
            self.center_position = self.last_center = self.start_pos
            self.moveto = self.end_pos
            logger.debug("%s: chase trigger on @ %s" % (self.name, intensity))
            self.moving = True
            self.setup_move()
            self._on_trigger(intensity, **kwargs)
        elif intensity == 0 and (self.trigger_state and not self.trigger_toggle
                and not self.bell_mode):
            self._off_trigger()
        elif intensity and self.trigger_state and self.trigger_toggle:
            logger.info("%s: chase trigger toggle off @ %s" % (self.name,
                intensity))
            self._off_trigger()

    def setup_move(self, moveto=None):
        """
        Sets up the move envelope from the current position
        """
        if moveto:
            # allow this to be a single method to be called
            # by others to both set a moveto, and start the move
            self.moveto = moveto
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
        self.move_complete = False
        if self.trigger_state:
            self.moving = True

    def _get_move_toward(self):
        return self.moveto

    def _set_move_toward(self, value):
        self.setup_move(moveto=value)

    move_toward = property(_get_move_toward, _set_move_toward)

    def _move_completed(self):
        # called at the end of a move, for looping, pong, etc
        # TODO while pulse paused at one end - this is firing multiple
        # times
        if self.continuation_mode == 'pong':
            if round(self.center_position) == self.end_pos:
                logger.debug("%s pong-end @ %s" % (self.name, self.end_pos))
                self.moveto = self.start_pos
            if round(self.center_position) == self.start_pos:
                self.moveto = self.end_pos
        elif self.continuation_mode == 'loop':
            # TODO the last_center reset is an easy one to miss, and should
            # be built into something else
            self.last_center = self.center_position = self.start_pos
            self.setup_move()
        else:
            self.moving = False
        self.move_complete = True
        if self.bell_mode and self.trigger_state:
            self._off_trigger()

    def reset_positions(self):
        # called in association with off trigger
        if (self.off_mode == "reverse"):
            if self.center_position == self.start_pos:
                self.moveto = self.end_pos
            else:
                self.moveto = self.start_pos
            self.moveto = int(self.moveto)
        else:  # all or follow
            if self.trigger_state:
                self.moveto = int(self.center_position)  # self.end_pos
            else:
                self.moveto = self.end_pos
            self.center_position = self.last_center = self.start_pos
            self.moveto = int(self.moveto)
            # setup_move only called from update_position if moveto != current
            # moveto in all off situations, current_moveto never changes.
            self.setup_move()
        self.moving = False

    def update_position(self, show):
        if self.current_moveto != self.moveto:
            self.setup_move()
        if self.moveto is not None:
                self.center_position = self.move_envelope.update(
                        show.time_delta)

    @property
    def update_active(self):
        return self.moving or super(Chase, self).update_active

    def update(self, show):
        # super handles sending update to sub-elements
        super(Chase, self).update(show)
        # always keep time delta updated
        if not self.trigger_intensity:
            if self.off_mode == "all":
                return
        if self.moving:
            self.update_position(show)
        self.render()
        for effect in self.effects:
            effect.update(show, [self])
        if self.moving and self.move_envelope.completed:
            # this reset should happen after the render
            # to give the final "frame" a chance to draw itself
            # this is not called if moveto is reached through rounding in
            # update_position
            # self.reset_positions()
            self._move_completed()

    def render(self):
        # TODO needs to handle reverse situations better
        if self.last_center is None:
            self.last_center = self.start_pos
        # TODO need to determine whether there shell be a generic anti-alias
        # support - Pulse currently does this in its own render
        current_center = int(self.center_position)
        if self.sweep:
            # trigger everything up to current center
            if self.last_center > current_center:
                [e.trigger(self.trigger_intensity) for
                        e in self.elements[current_center:self.last_center]]
            else:
                [e.trigger(self.trigger_intensity) for
                        e in self.elements[self.last_center:current_center]]
        else:
            # trigger only the width
            [e.trigger(0) for e in self.elements]
            if current_center > self.moveto:
                # note, currently there is no difference between start and end
                # based on direction, the width is always to the left of the
                # current center - more of a sweep effect can be made with
                # bell modes on the sub elements
                start = max(self.lower_bound, current_center - self.width)
                end = current_center
            else:
                start = max(self.lower_bound, current_center - self.width)
                end = current_center
            if self.sweep:
                intensity = self.trigger_intensity
            else:
                # TODO - we can't get the original trigger intensity anymore
                # it shouldn't be 1 - the fix will be to make sweep renders
                # above work with the trigger state instead of intensity?
                intensity = 1
            [e.trigger(intensity) for e in self.elements[start:end]]
        self.last_center = current_center

    @property
    def upper_bound(self):
        return max(self.start_pos, self.end_pos)

    @property
    def lower_bound(self):
        return min(self.start_pos, self.end_pos)


class Spawner(BaseLightElement):
    def __init__(self, *args, **kwargs):
        super(Spawner, self).__init__(*args, **kwargs)
        self.model = kwargs.get('model', None)
        self.show = kwargs.get('show')
        self.network = kwargs.get('network')
        self.spawned = {}
        self.channels = []
        self.unique_per_key = True
        self._spawn_counter = 0

    def spawn(self, key):
        if self.unique_per_key and key in self.spawned:
            return self.spawned[key]
        instance = deepcopy(self.model)
        self.show.add_element(instance)
        if self.unique_per_key:
            self.spawned[key] = instance
        else:
            self.spawned[self._spawn_counter] = instance
            self._spawn_counter += 1
        # TODO need a recurse way to add only the end elements
        # that actually have channels
        [self.network.add_element(e) for e in instance.elements]
        try:
            instance.spawned()
        except AttributeError:
            pass
        return instance

    def update(self, show):
        # remove completed items
        remove = []
        # return
        for key, e in self.spawned.items():
            # TODO need a more abstract way of determining if element is
            # 'complete'
            if not e.update_active:
                # print 'removing element for ', key
                self.show.remove_element(e)
                remove.append(key)
        for key in remove:
            del(self.spawned[key])

    def trigger(self, intensity, **kwargs):
        if intensity > 0:
            key = kwargs['key'][1]
            new_spawn = self.spawn(key)
            new_spawn.bell_mode = True
            new_spawn.continuation_mode = None
            new_spawn.trigger(intensity)


class HitPulse(Spawner):

    def __init__(self, *args, **kwargs):
        super(HitPulse, self).__init__(*args, **kwargs)
        self.elements = []
        self.width = 8
        self.network = None

    def spawn(self, key):
        if key in self.spawned:
            return self.spawned[key]
        center = key
        # TODO the roles of trigger and spawn need to be better divided
        random_hue = random.random()
        chase_pair = LightGroup()
        for rev in (True, False):
            chase = Chase(
                    start_pos=0,
                    end_pos=self.width,
                    speed=.15,
                    # move_tween=tween.OUT_EXPO,
                    )
            chase.off_mode = "reverse"
            # chase.bell_mode = True
            if rev:
                elements = self.elements[center - self.width:center]
                elements.reverse()
            else:
                elements = self.elements[center:center + self.width]
            chase.elements = [deepcopy(x) for x in elements]
            for x in chase.elements:
                x.hue = random_hue
                self.network.add_element(x)
                # self.show.add_element(x, network=self.network)
            chase_pair.elements.append(chase)
            # chase_pair.elements = [deepcopy(x) for x in self.elements[30:31]]
            # self.show.add_element(chase)

            # chase_pair.elements.extend(chase.elements)
            # for x in chase_pair.elements:
                # x.hue = random_hue
                # self.network.add_element(x)

        self.spawned[key] = chase_pair
        self.show.add_element(chase_pair)
        return chase_pair

    def trigger(self, intensity, **kwargs):
        if intensity > 0:
            # TODO need input range
            # key = kwargs['key'][1] - 50
            # TODO need to handle trigger's more abstractly for OSC etc
            # TODO need to have self.spawned be a dict with keys so that
            # off triggers can find their matching spawned item, to support
            # more than just bell_mode
            key = kwargs['key'][1]
            spawned_pair = self.spawn(key=key)
            spawned_pair.trigger(intensity)
        else:
            # off trigger
            key = kwargs['key'][1]
            if key in self.spawned:
                # may not be present if bell mode already removed
                spawned_pair = self.spawned[key]
                spawned_pair.trigger(0)


class Pulse(object):
    """
    handles the rendering of a pulse in the abstract sense
    a range of values that change over distance
    """
    def __init__(self,
            left_width=3,
            left_shape=tween.LINEAR,
            right_width=3,
            right_shape=tween.LINEAR,
            **kwargs):

        self.left_width = left_width
        self.left_shape = left_shape
        self.right_width = right_width
        self.right_shape = right_shape
        self.nodes = []  # a list of element values for pulse
        self.node_range = []  # index range of current pulse
        self.current_position = 0

    def set_current_nodes(self):
        """
        the node array becomes a list of values - generally for intensity
        that describes the left and right shape of the pulse around
        the center_position.

        The node_range specifies the location start and end of the pulse
        overall
        """
        node_offset = self.center_position % 1
        left_of_center = math.floor(self.center_position)
        far_left = int(left_of_center - self.left_width)
        self.nodes = []
        for n in range(self.left_width + 1):
            self.nodes.append(self.left_shape(
                        n + node_offset, 1, -1, self.left_width + 1.0))
        if far_left >= 1:
            self.nodes.append(0)
            far_left -= 1
        self.nodes.reverse()
        for n in range(1, self.right_width + 1):
            self.nodes.append(self.right_shape(
                    max(0, n - node_offset), 1, -1, self.right_width + 1.0))
        self.nodes.append(0)
        self.node_range = range(far_left, far_left + len(self.nodes))
        logger.debug("NodeData:")
        logger.debug(self.node_range)
        logger.debug(self.nodes)


class PulseChase(Chase, Pulse):
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
            # TODO once the kwargs settle down - make them explicit
            left_width=3,
            left_shape=tween.LINEAR,
            right_width=3,
            right_shape=tween.LINEAR,
            **kwargs):

        super(PulseChase, self).__init__(**kwargs)
        Pulse.__init__(self, **kwargs)
        self.anti_alias = True
        self.continuation_mode = 'pong'

    def update(self, show):
        super(PulseChase, self).update(show)
        logger.debug("%s Centered @ %s -> %s" %
                (self.name, self.center_position, self.end_pos))

    def render(self):
        self.set_current_nodes()
        for i, e in enumerate(self.elements):
            e.trigger(0)
            if i in self.node_range:
                # TODO issue here with a moving pulse:
                # how does the element handle multiple on triggers
                # the trigger 0 is needed otherwise the leading edge just stays
                # dim
                e.trigger(self.nodes[i - self.node_range[0]])


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
        # self.scenemanager = SceneManager()
        self.frame_delay = 1 / self.frame_rate
        self.running = True
        self.named_elements = {}
        self.default_network = DefaultNetwork()
        self.networks.append(self.default_network)
        self.time_delta = 0
        self.recent_frames = deque()
        self.average_framerate = self.frame_delay
        self.frame = 0
        self.elements = []

    def add_element(self, element, network=None):
        if network:
            network.add_element(element)
            if network not in self.networks:
                self.networks.append(network)
        if element not in self.elements:
            self.elements.append(element)

    def remove_element(self, element, network=None):
        if hasattr(element, 'elements') and element.elements:
            for sub_element in element.elements:
                self.remove_element(sub_element)
        for network in self.networks:
            network.remove_element(element)
        try:
            self.elements.remove(element)
            return True
        except ValueError:
            return False

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
        # needed as params may be changed between __init__ and run_live
        for n in self.networks:
            n.init_data()
        self.frame_delay = 1.0 / self.frame_rate

    def frame_average(self, frame):
        self.recent_frames.append(frame)
        frame_count = len(self.recent_frames)
        if frame_count > 8:
            self.recent_frames.popleft()
            frame_count -= 1
        elif frame_count == 0:
            return frame
        return sum(self.recent_frames) / frame_count

    def step(self, count=1, speed=1):
        """
        Simulate a step or steps in main loop
        """
        for i in range(count):
            self.timecode += self.frame_delay
            self.time_delta = self.frame_delay
            self.update()
            for n in self.networks:
                n.send_data()
            if speed and count > 1 and i < (count - 1):
                time.sleep((1 / speed) * self.frame_delay)

    def run_live(self):
        self.init_show()
        self.show_start = time.time()
        self.timecode = 0
        while self.running:
            # projected frame event time
            now = time.time() + self.frame_delay
            timecode = now - self.show_start
            self.time_delta = timecode - self.timecode
            self.timecode = timecode
            self.update()
            post_update = time.time()
            # how long did this update actually take
            effective_frame = post_update - (now - self.frame_delay)
            effective_framerate = self.frame_average(effective_frame)
            discrepancy = effective_framerate - self.frame_delay
            if discrepancy > .01:
                self.frame_delay += .01
                if discrepancy > .3:
                    warnings.warn("Slow refresh")
            elif discrepancy < -.01 and self.frame_delay > 1 / self.frame_rate:
                # we can speed back up
                self.frame_delay -= .01
            self.frame += 1
            remainder = self.frame_delay - effective_frame
            if remainder > 0:
                # we finished early, wait to send the data
                # TODO this wait could/should happen in another thread that
                # handles the data sending - but currently sending the data
                # is fast enough that this can be investigated later
                time.sleep(remainder)
            # pre_send = time.time()
            for n in self.networks:
                n.send_data()
            if self.frame == 40:
                # print [e.channels for e in self.networks[1].elements]
                print('framerate: ', 1 / self.frame_delay, " Remainder: ",
                        remainder)
                self.frame = 0

    def update(self):
        """The main show update command"""
        # self.scenemanager.update(self)
        for element in self.elements:
            if element.last_update != self.timecode:
                # avoid updating the same element twice
                element.update(self)
                element.last_update = self.timecode
        for e in self.effects:
            e.update(self)
