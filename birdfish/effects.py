"""some notes on effects:

an effect needs to be added to a show because it tracks things over time.

base class for many effects is a complex cycle class that defines segments of an effect

"""

from lights import *
import pytweener

# blend modes
NORMAL = 1
DARKEN = 2
LIGHTEN = 3

# @@ really just need a CycleSegment, using classes can ask about it's tween or duration as needed
class CycleSegment(object):
    def __init__(self,*args, **kwargs):
        self.duration = kwargs.get("duration",1)
        self.values = kwargs.get("values",{})
        self.name = kwargs.get("name","cyclesegment")

class CycleTransitionSegment(CycleSegment):
    def __init__(self,*args,**kwargs):
        super(CycleTransitionSegment, self).__init__(*args, **kwargs)
        self.tweentype = "linear"

# @@ Need a segment generator class
# which would have a duration and then be able to generate effects segments 
# per its own algorithm.  Good for things like flicker or lightening.
# can also have its own duration

class ModulationCycle(LightGroup):
    """Notes:
    need to be smart about items with 0 duration

    3 sets of segments - attack - standard (sustain) - release

    segments are not anything like chase elements - in that they effect all elements of the group equally
    they are segments of the effect over time.

    attack if they exist, are run on trigger, then sustains are played (and optionally looped)

    then on trigger off the main segments are run through if finish_cycle is true, then release segments are run

    need a way to denote an infinite sustain duration - or just have single element standard

    phases: 0 quiet
            1 attack
            2 sustain
            3 release
    """
    def __init__(self,*args,**kwargs):
        super(ModulationCycle, self).__init__(*args, **kwargs)
        self.attack_segments = []
        self.standard_segments = []
        self.release_segments = []
        self.segment_sets = []
        self.effect_values = []
        self.blend = NORMAL # blend mode, ala photoshop layers
        self.looping = True
        self.finish_cycle = True
        self.phase = 0
        self.tweener = pytweener.Tweener()
        self.trigger_intensity = 0
        self.index = 0 # index of current segment set
        self.current_segments = None
        self.last_update = 0
        self.running = False
        self.wait_till = 0

    def segment_tween_done(self):
        print "tween done"

    def init_values(self,segments):
        for s in segments:
            for k in s.values.keys():
                if k not in self.effect_values:
                    self.effect_values.append(k)
                if k not in self.__dict__:
                    self.__dict__[k] = 0

    def add_tween(self):
        current_segment = self.current_segments[self.index]
        kwargs = {  "tweenTime":current_segment.duration,
                "tweenType":    getattr(self.tweener, current_segment.tweentype.upper()),
                "onCompleteFunction": self.segment_tween_done
                 }
        for k,v in current_segment.values.items():
            change = v - self.__dict__[k]
            kwargs[k] = change
        # kwargs.update(current_segment.values)
        tw = self.tweener.addTween(self, **kwargs)

    def update_values(self):
        values = self.effect_values # self.current_segments[self.index].values.keys()
        for a in values:
            for e in self.elements:
                if hasattr(e,a):
                    data = self.__dict__[a]
                    # @@ here is where a blend mode is applied
                    # have to probe values
                    if self.blend == NORMAL:
                        setattr(e,a,data)
                    elif self.blend == DARKEN:
                        v = min(data,getattr(e,a))
                        # print "darken %s" % v
                        setattr(e,a,v)
                    elif self.blend == LIGHTEN:
                        v = max(data,getattr(e,a))
                        setattr(e,a,data)



    def advance(self):
        # print "advancing, current index %s" % self.index
        if self.index == len(self.current_segments) -1:
            self.index = 0
            # self.last_update = 0
            if self.phase == 1:
                if self.standard_segments:
                    self.phase = 2
                    self.current_segments = self.standard_segments
                    return True
                elif self.release_segments:
                    self.phase = 3
                    self.current_segments = release_segments
                    return True
            elif self.phase == 2:
                if self.looping and self.trigger_intensity:
                    return True
                elif self.release_segments:
                    self.init_values(self.release_segments)
                    self.phase = 3
                    self.current_segments = release_segments
                    return True
            # if we get to here, we are at the end of phase 3 (release segments)
            self.phase = 0 # a bit superfluous
            self.running = False
        else:
            self.index += 1

    def update(self,show):
        # print 'update',self.running
        if not self.running:
            return False
        # print 'running',self.running
        if self.wait_till:
            if show.timecode < self.wait_till:
                # print "waiting"
                # still need to force update the values to maintain the visual
                # effect for each frame
                self.update_values()
                return False
            else:
                self.advance()
                self.wait_till = 0
                return False
        if not self.last_update:
            # @@ can't set this from trigger - since don't have access to show
            self.last_update = show.timecode
            print "setting start time"
            return False
        time_delta = show.timecode - self.last_update
        self.last_update = show.timecode

        if self.tweener.hasTweens():
            self.tweener.update(time_delta)
            self.update_values()
            if not self.tweener.hasTweens():
                self.advance()
        else:
            # either starting a new tween, or new duration item
            current_segment = self.current_segments[self.index]
            print "updating: %s, current self.intensity: %s" % (current_segment.name,self.intensity)
            if current_segment.duration:
                if not current_segment.values:
                    # duration only item
                    # print "duration only item"
                    self.wait_till = show.timecode + current_segment.duration
                    self.update_values()
                else:
                    # tween item
                    print "tween item"
                    self.add_tween()
                    self.last_update = show.timecode
            elif current_segment.values:
                # no duration, update immediately
                # print "immediate update item"
                self.__dict__.update(current_segment.values)
                self.update_values()
                self.advance()
            # in this case we have a segment with no duration, not values
            # @@ could log warnting here 
            else:
                # print "straigt advance"
                self.advance()


    def trigger(self,trigger_intensity):
        print ("trigger")
        # print trigger_intensity
        self.trigger_intensity = trigger_intensity
        self.index = 0
        self.last_update = 0

        if trigger_intensity:
            if self.attack_segments:
                self.current_segments = self.attack_segments
                self.init_values(self.attack_segments)
                self.phase = 1
            else:
                print "starting with standard segments"
                self.current_segments = self.standard_segments
                self.init_values(self.standard_segments)
                self.phase = 2
            self.running = True
        else:
            if self.finish_cycle:
                print "finishing cycle"
                # finish out primary segments
                # basically ignore this trigger
                return True
            elif self.release_segments:
                self.init_values(self.release_segments)
                # execute release segments
                self.current_segments = self.release_segments
                self.phase = 3
                return True
            else:
                print "ending now"
                self.running = False



class Strobe(ModulationCycle):
    # @@ note that this does not provide for a random strobe
    def __init__(self,*args, **kwargs):
        super(Strobe, self).__init__(*args, **kwargs)
        flash_duration = kwargs.get("flash_duration",.1)
        hz = kwargs.get("hz",3)
        flash_on = CycleTransitionSegment(duration=0,values={"intensity":255},name="flash_on")
        flash = CycleSegment(duration = flash_duration,name="flash")
        flash_off = CycleTransitionSegment(duration=0,values={"intensity":0},name="flash_off")
        black = CycleSegment(duration = ((1 / hz) - flash_duration),name="black")
        self.standard_segments = [flash_on, flash, flash_off, black]


class ADSREnvelope(ModulationCycle):
    """an object that provides an ADSR envelope for shaping light intensity over time"""

    def __init__(self, attack=0, decay=0, sustain=255, release=0, attribute="intensity"):
        super(ADSREnvelope, self).__init__()
        attack_segment = CycleTransitionSegment(name="attack",duration=attack,values={attribute:255})
        decay_segment = CycleTransitionSegment(name="decay", duration=decay,values={attribute:sustain})
        sustain_segment = CycleSegment(name="sustain", duration=-1)
        release_segment = CycleTransitionSegment(name="release", duration=release,values={attribute:0})
        self.attack_segments = [attack_segment, decay_segment]
        self.standard_segments = [sustain_segment]
        self.release_segments = [release_segment]


class Pulser(ModulationCycle):
    def __init__(self,*args, **kwargs):
        super(Pulser, self).__init__(*args, **kwargs)
        attribute = kwargs.get("attribute","intensity")
        attribute_max = kwargs.get("max",255)
        attribute_min = kwargs.get("min",0)
        duration_on = kwargs.get('duration_on',.5)
        duration_off = kwargs.get('duration_off',.5)
        tween_in = kwargs.get('tween_in','linear')
        tween_out = kwargs.get('tween_out','linear')
        rise = CycleTransitionSegment(duration=duration_on,tweentype=tween_in,name="rise",values={attribute:attribute_max})
        fall = CycleTransitionSegment(duration=duration_off,tweentype=tween_out,name="fall",values={attribute:attribute_min})
        self.standard_segments = [rise,fall]


