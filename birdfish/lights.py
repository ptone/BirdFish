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
from birdfish.output.base import DefaultNetwork

from birdfish.log_setup import logger

# logger = logging.getLogger('birdfish')
# logger.setLevel(logging.INFO)


class LightingNetworkElement(object):
    """This item represents an element that provides channel data"""

    def __init__(self, start_channel=1, *args, **kwargs):
        self.name = kwargs.get('name', "baselight")
        # signal intensity is the value set by the note on velocity -
        # does not reflect current brightness
        self.channels = {}

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


class BaseLightElement(object):
    """
    This class handles trigger events, and is updated with the show timeline
    """

    # TODO need to factor the ADSR related parts out of this class

    def __init__(self, *args, **kwargs):
        self.trigger_intensity = 0.0
        self.intensity = 0.0
        self.universe = 1
        self.bell_mode = False
        self.name = kwargs.get("name", "unnamed_LightElement")
        self.adsr_envelope = ADSREnvelope(**kwargs)
        # a simple element has values set externally and does not update
        self.simple = False
        # TODO I'm pretty sure trigger_state is entirely replaceable with
        # trigger_intensity every place it is used
        self.trigger_state = 0
        self.trigger_toggle = False
        self.effects = []
        self.pre_update_effects = []

        # self.logger = logging.getLogger(
                # "%s.%s.%s" % (__name__, "LightElement", self.name))

    def bell_reset(self):
        self._off_trigger()

    def update(self, show):
        if (self.simple or not (self.intensity or self.trigger_intensity)):
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
        return self.intensity

    def set_intensity(self, intensity):
        # mostly to be overridden by subclasses
        self.intensity = intensity

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
        """convenience for off"""
        self.trigger(0.0)


class LightElement(BaseLightElement, LightingNetworkElement):
    """
    This is a composed class that represents a basic light that has both
    behaviors and channel data
    """
    def __init__(self, *args, **kwargs):
        BaseLightElement.__init__(self, *args, **kwargs)
        LightingNetworkElement.__init__(self, *args, **kwargs)


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
        """
        updates hue property from RGB values, RGB is always updated when hue
        changed
        """
        adjusted_rgb = [x * self.intensity for x in [
            self.red, self.green, self.blue]]
        h, s, v = colorsys.rgb_to_hsv(*tuple(adjusted_rgb))
        self._hue = h
        self._saturation = s

    def update_rgb(self):
        hue = self._hue
        saturation = self._saturation
        if 'intensity' in self.channels.values():
            # if the fixture has its own intensity slider - always calc RGB
            # values at full intensity
            intensity = 1.0
        else:
            intensity = self.intensity
        # this funct takes all 0-1 values
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, intensity)
        # here intensity is assumed to be full, as HSV to RGB sets RGB values
        # accordingly
        self.red = r
        self.green = g
        self.blue = b

    def _get_hue(self):
        # TODO need to update with function in case r,g,b were updated other
        # than through hue
        return self._hue

    def _set_hue(self, hue):
        self._hue = hue
        self.update_rgb()

    def _get_saturation(self):
        return self._saturation

    def _set_saturation(self, saturation):
        self._saturation = saturation
        self.update_rgb()
        # TODO concept of intensity should be converted to raw RGB for base RGB
        # light no assumption of 4th channel

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
        self.update_active = False

    def trigger(self, sig_intensity, **kwargs):
        if sig_intensity:
            intensity = min(self.max_intensity, sig_intensity)
            [x.trigger(intensity) for x in self.effects]
            self.trigger_state = 1
            self.update_active = True
        else:
            self.trigger_state = 0
            intensity = 0.0
        [x.trigger(intensity) for x in self.effects]
        [l.trigger(intensity) for l in self.elements]

    def set_intensity(self, intensity):
        # the group element always has a pseudo-intensity of 1
        [e.set_intensity(e.intensity * intensity) for e in self.elements]

    def update(self, show):
        if self.trigger_state or self.update_active:
            elements_active = False
            for element in self.elements:
                element.update(show)
                # determine if any elements are still active - ie in release
                elements_active = elements_active or element.trigger_intensity
            # set our own active state based on whether
            # any element is still active
            self.update_active = elements_active


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

    def update(self, show):
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
                [e.trigger(self.trigger_intensity) for
                        e in self.elements[
                            current_center:(current_center + self.width)]]
            else:
                [e.trigger(self.trigger_intensity) for
                        e in self.elements[
                            current_center - self.width:current_center]]
        self.last_center = current_center


class Spawner(object):
    def __init__(self, *args, **kwargs):
        self.model = kwargs.get('model', None)
        self.show = kwargs.get('show')
        self.network = kwargs.get('network')
        self.spawned = {}
        self.channels = []

    def spawn(self):
        instance = deepcopy(self.model)
        # assuming we have elements - no point in spawning simple items
        instance.elements = self.model.elements
        self.show.add_element(instance)
        # self.network.add_element(instance)
        return instance

    def update(self, show):
        # remove completed items
        for e in self.spawned:
            if e.move_complete:
                self.show.remove_element(e)
                self.spawned.remove(e)

    def trigger(self, intensity, **kwargs):
        if intensity > 0:
            new_spawn = self.spawn()
            new_spawn.bell_mode = True
            new_spawn.continuation_mode = None
            new_spawn.trigger(intensity)
            self.spawned.append(new_spawn)


class HitPulse(Spawner):

    def __init__(self, *args, **kwargs):
        super(HitPulse, self).__init__(*args, **kwargs)
        self.elements = []
        self.width = 8
        self.network = None

    def spawn(self, center):
        pair = []
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
                chase.elements = self.elements[center - self.width:center]
                chase.elements.reverse()
            else:
                chase.elements = self.elements[center:center + self.width]
            self.show.add_element(chase)
            chase.elements = [deepcopy(x) for x in chase.elements]
            for x in chase.elements:
                self.show.add_element(x)
                self.network.add_element(x)
                x.hue = random_hue
            pair.append(chase)
        pair.reverse()
        chase_pair.elements = pair
        return chase_pair

    def update(self, show):
        # remove completed items
        remove = []
        # return
        for key, e in self.spawned.items():
            # TODO need a more abstract way of determining if element is
            # 'complete'
            if e.trigger_intensity == 0 and e.move_complete and not e.moving:
                for element in e.elements:
                    self.show.remove_element(element)
                    self.network.remove_element(element)
                self.show.remove_element(e)
                remove.append(key)
        for key in remove:
            del(self.spawned[key])

    def trigger(self, intensity, **kwargs):
        if intensity > 0:
            # TODO need input range
            # key = kwargs['key'][1] - 50
            # TODO need to handle trigger's more abstractly for OSC etc
            # TODO need to have self.spawned be a dict with keys so that
            # off triggers can find their matching spawned item, to support
            # more than just bell_mode
            key = kwargs['key'][1]
            print key
            spawned_pair = self.spawn(center=key)
            for new_spawn in spawned_pair:
                new_spawn.trigger(intensity)
            self.spawned[key] = spawned_pair
        else:
            # off trigger
            key = kwargs['key'][1]
            if key in self.spawned:
                # may not be present if bell mode already removed
                spawned_pair = self.spawned[key]
                [spawn.trigger(0) for spawn in spawned_pair]


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
        self.dmx_keep_alive = True
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
            if self.frame == 20:
                self.frame = 0

    def update(self):
        """The main show update command"""
        # self.scenemanager.update(self)
        for element in self.elements:
            element.update(self)
        for e in self.effects:
            e.update(self)
