from collections import deque
import colorsys
# from ola.OlaClient import OlaClient, Universe
# import client_wrapper
import time
# import select
import random
import logging
import pytweener
from scene import SceneManager
from birdfish.output.base import DefaultNetwork


logger = logging.getLogger(__name__)

frame_rate = 30


class BaseLightElement(object):
    """docstring for BaseLightElement"""

    """@@ possible additions to support overlay:
    if when the value of a channel attribute is changed, set a flag containing
    show timecode.  When a subsequent meta element goes to change a value, it
    checks this flag, and if set to current show timecode, will only change the
    value based on some rule - say only brighten or increase the value.  This
    would support some things like having different chases pass by each other.
    """

    def __init__(self, start_channel=1, *args, **kwargs):
        self.name = kwargs.get('name', "baselight")
        self.effects = []
        # signal intensity is the value set by the note on velocity -
        # does not reflect current brightness
        self.trigger_intensity = 0
        self.intensity = 0
        self.channels = {}
        self.last_updated = 0
        self.channels[start_channel] = 'intensity'
        self.frame_rate = 40

    def update_data(self, data):
        """
        data is an array of data (ie DMX) that should be updated
        with this light's channels
        """
        for channel, value in self.channels.items():

            # if channel == 2:
            # print '%s, %s, %s' % (channel, value, int(getattr(self,value)))
            val = int(getattr(self, value))
            data[channel - 1] = int(val)
            # no easy way to have more than one light on the same channel would
            # need some way to track which objs have updated a slot - so that
            # each has a shot at increasing it.  @@ need a way to check for
            # channel collisions to avoide unexpected results dmx[channel-1]
            # = max (dmx_val,dmx[channel-1]) #zero index adjust??

class LightElement(BaseLightElement):


    def __init__(self, *args, **kwargs):
        super(LightElement, self).__init__(*args, **kwargs)
        self.env_phase = 0 # adsr 1234
        self.attack = 0
        self.decay = 0
        self.sustain = 1 # should be a value between 0 and 1
        self.release = 0
        self.trigger_intensity = 0
        self.attack_tween = "linear"
        self.decay_tween = "linear"
        self.release_tween = "linear"
        self.env_step = 1
        self.universe = 1
        self.tweener = pytweener.Tweener()
        self.bell_mode = False
        self.last_update = 0
        self.shape_tween = False
        self.name = kwargs.get("name", "unnamed_LightElement")
        self.logger = logging.getLogger(
                "%s.%s.%s" % (__name__, "LightElement", self.name))

    def set_special_state(self, state_dict):
        defaults = self.__dict__.copy()
        if 'defaults' in defaults:
            del(defaults['defaults'])
        self.defaults = defaults
        self.__dict__.update(state_dict)

    def restore_defaults(self):
        if hasattr(self, "defaults"):
            self.__dict__.update(self.defaults)

    def update(self, show):
        if hasattr(self, 'debug'):
            if self.intensity and self.env_phase == 4:
                self.logger.debug("intensity: %s" % self.intensity)
            # if self.env_phase:
                # print self.env_phase
        if (not (self.intensity or self.trigger_intensity)) or self.env_phase == 3:
            # light is inactive or in sustain mode
            return False
        if not self.last_update:
            # can't set this from trigger - since don't have access to show
            self.last_update = show.timecode
            return False
        time_delta = show.timecode - self.last_update
        self.last_update = show.timecode
        # self.last_used_intensity = self.intensity
        if self.tweener.hasTweens():
            self.tweener.update(time_delta)
            # if the only tween that existed was already complete
            # tweener.update will clear it out, then a check will show no
            # active tweens
            if not self.tweener.hasTweens():
                self.adsr_advance()
        else:
            self.adsr_advance()

        # moved dmx update to show update, to accomodate effects
        # self.dmx_update(show.universes[self.universe].dmx)
        # if self.last_used_intensity != self.intensity:
        #     print int(self.intensity)
        return self.intensity

    def adsr_advance(self):
        if hasattr(self.shape_tween, 'complete'):
            # clear out previous tween
            self.shape_tween.complete = True
        if self.env_phase == 1:
            if self.decay:
                self.env_phase = 2
                self.add_shape_tween('decay')
            else:
                # no decay, enter sustain
                self.env_phase = 3
        elif self.env_phase == 2:
            if not self.sustain:
                # decayed to off, shut element down
                self.intensity = self.env_phase = self.trigger_intensity = 0
            else:
                # decay is complete, enter sustain
                if self.bell_mode:
                    # no sustain in bell mode
                    if self.release:
                        self.do_release()
                    else:
                        # end
                        # @@ perhaps catch and warn confusing condition if bell
                        # mode chosen but no attack, decay, or release
                        self.intensity = self.env_phase = self.trigger_intensity = 0
                else:
                    self.env_phase = 3
        elif self.env_phase == 3:
            if self.bell_mode:
                # jump to release
                if self.release:
                    self.do_release()
                else:
                    # turn off now
                    self.intensity = self.env_phase = self.trigger_intensity = 0
            else:
                # we stay in sustain mode until an off trigger event
                pass
        elif self.env_phase == 4:
            # release is all done - shut off
            self.intensity = self.env_phase = self.trigger_intensity = 0

    def do_release(self):
        logger.debug("release")
        if self.release:
            self.logger.debug("has release tween")
            self.env_phase = 4
            self.add_shape_tween('release')
        else:
            self.logger.debug("no tween, shutting off")
            self.intensity = self.env_phase = self.trigger_intensity = 0

    def tween_done(self):
        self.logger.debug("tween done")
        # this update will clear out completed tweens to hasTweens will return correct value
        self.tweener.update(0)

    def add_shape_tween(self, phase):
        if hasattr(self.shape_tween, 'complete'):
            # clear out previous tween
            self.shape_tween.complete = True
        if phase == 'attack':
            intensity_delta = self.trigger_intensity
        elif phase == 'decay':
            intensity_delta = (self.trigger_intensity * self.sustain) - self.intensity
        elif phase == 'release':
            intensity_delta = -self.intensity
        self.shape_tween = self.tweener.addTween(
                self, # the object being tweened
                tweenTime=getattr(self, phase),
                tweenType=getattr(self.tweener, getattr(self, "%s_tween" % phase).upper()),
                onCompleteFunction = self.tween_done,
                intensity=intensity_delta,  # the attribute being tweened
                                                )
        self.last_update = 0

    def trigger(self, intensity, **kwargs):
        """Trigger a light with code instead of midi"""
        # @@ need toggle mode implementation here
        if intensity > 0:  # or note off message
            if self.tweener.hasTweens() and self.bell_mode:
                self.logger.debug("ignoring on trigger")
                return
            self.trigger_intensity = intensity
            self.logger.debug("trigger on")
            self.intensity = 0  # reset light on trigger
            self.env_phase = 1
            if self.attack:
                self.logger.debug("has attack - adding tween")
                self.add_shape_tween('attack')
            else:
                self.intensity = intensity
        else:
            if self.bell_mode:
                # ignore release in bell mode
                return
            elif self.release:
                self.trigger_intensity = intensity
                self.logger.debug("trigger off - release")
                self.do_release()
            else:
                if hasattr(self.shape_tween, 'complete'):
                    # clear out previous tween
                    self.logger.debug("cancelling tween")
                    self.shape_tween.complete = True
                self.logger.debug("trigger off, no release, shutting off")
                self.intensity = self.env_phase = self.trigger_intensity = 0


    def off(self):
        """convenience for off"""
        self.trigger(0)


class RGBLight(LightElement):
    RED = (255, 0, 0)
    GREEEN = (0, 255, 0)
    BLUE = (0, 0, 255)

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

    def trigger(self, intensity, **kwargs):
        self.intensity = intensity
        self.update_rgb()
        super(RGBLight, self).trigger(intensity, **kwargs)

    def update(self, show):
        return_value = super(RGBLight, self).update(show)
        # TODO - this funciton needed when tweening hue - but can't be used
        # tweening RGB directly
        # self.update_rgb()
        return return_value

    # @@ need to address the attribute of intensity in the context of RGB
    def update_hue(self):
        """updates hue property from RGB values, RGB is always updated when hue changed"""
        adjusted_rgb = [(x / 255.0) * (self.intensity / 255.0) for x in [
            self.red, self.green, self.blue]]
        h, s, v = colorsys.rgb_to_hsv(*tuple(adjusted_rgb))
        # hue and saturation stay as 0-1 values, not 0-255 since they are assumed to be not DMX
        self._hue = h * 255
        self._saturation = s * 255
        # value = intensity - this will need to be overridden in RGB lights that use a 4th channel for intensity
        # self.intensity = v * 255

    def update_rgb(self):
        hue = self._hue / 255.0
        saturation = self._saturation / 255.0
        if 'intensity' in self.channels.values():
            # if the fixture has its own intensity slider - always calc RGB values at full intensity
            intensity = 1.0
        else:
            intensity = self.intensity / 255.0
        # this funct takes all 0-1 values
        # print "intensity %s " % intensity
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, intensity)
        # here intensity is assumed to be full, as HSV to RGB sets RGB values accordingly
        # print "result %s, %s, %s" % (r,g,b)
        self.red = r * 255.0
        self.green = g * 255.0
        self.blue = b * 255.0
        # self.intensity = 255

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

class LightGroup(BaseLightElement):
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
        self.element_initialize = {}
        self.logger = logging.getLogger("%s.%s.%s" % (__name__, "LightGroup", self.name))

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
        if sig_intensity and self.element_initialize:
            self.set_special_state(self.element_initialize)
        for l in self.elements:
            l.trigger(intensity)
        if (not sig_intensity) and self.element_initialize:
            self.restore_defaults()

    def set_special_state(self, state_dict):
        for l in self.elements:
            l.set_special_state(state_dict)

    def restore_defaults(self):
        for l in self.elements:
            l.restore_defaults()

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

class LightChase(LightGroup):
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
        self.logger = logging.getLogger("%s.%s.%s" % (__name__, "LightChase", self.name))


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

        self.logger.debug("seq index %s" % self.index)


        if self.intensity:
            # this approach to pulse, will handle direction switches easily
            while intindex > self.last_added_index:
                self.last_added_index += 1
                self.logger.debug("self.last_added_index")
                self.logger.debug(self.last_added_index)
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
            self.logger.debug("end reached")
            if self.randomize:
                random.shuffle(self.elements)

            if self.animation_mode == "loop":
                # reset index
                self.logger.debug('looping')
                self.logger.debug(self.loop_delay)
                self.logger.debug(self._delay_till)
                if self.loop_delay and (self._delay_till == 0):
                    self._delay_till = show.timecode + self.loop_delay
                    return
                self.logger.debug("loop reset")
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
            self.logger.debug("chase trigger: OFF")
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
