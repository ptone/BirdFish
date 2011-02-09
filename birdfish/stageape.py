from lights import *

class StageApeLight(RGBLight):
    def __init__(self, *args, **kwargs):
        super(StageApeLight, self).__init__(*args, **kwargs)
        self.function_slider = 255
        startchannel = kwargs.get('start_channel',1)
        # @@ may need to wipe and reset channels dict in subclass
        self.channels[startchannel] = 'function_slider'
        self.channels[startchannel+1] = 'intensity'
        self.channels[startchannel+2] = 'red'
        self.channels[startchannel+3] = 'green'
        self.channels[startchannel+4] = 'blue'
        self.red = 255
        self.green = 255
        self.blue = 255
        
    # def trigger(self, *args, **kwargs):
    #     print "stageape trigger"
    #     print args
    #     print kwargs
    #     super(StageApeLight, self).trigger(*args, **kwargs)
    #
    
class StageApeWhite64(LightElement):
    def __init__(self, *args, **kwargs):
        super(StageApeWhite64, self).__init__(*args, **kwargs)
        startchannel = kwargs.get('start_channel',1)
        self.channels[startchannel] = 'strobe'
        self.channels[startchannel+1] = 'intensity'
        self.strobe = 0

class StageApe64RGB(RGBLight):
    def __init__(self, *args, **kwargs):
        super(StageApe64RGB, self).__init__(*args, **kwargs)
        startchannel = kwargs.get('start_channel',1)
        self.channels[startchannel] = 'green'
        self.channels[startchannel+1] = 'red'
        self.channels[startchannel+2] = 'blue'
        self.channels[startchannel+3] = 'color' #should be zero for other control
        self.channels[startchannel+4] = 'color_change'
        self.channels[startchannel+5] = 'strobe'
        self.channels[startchannel+6] = 'intensity'
        self.color = 0
        self.color_change = 255
        self.strobe = 0

class StageApeScreen(RGBLight):
    def __init__(self, *args, **kwargs):
        super(StageApeScreen, self).__init__(*args, **kwargs)
        startchannel = kwargs.get('start_channel',1)
        self.channels[startchannel] = 'red'
        self.channels[startchannel+1] = 'green'
        self.channels[startchannel+2] = 'blue'
        self.channels[startchannel+3] = 'color_change' #should be zero for other control
        self.channels[startchannel+4] = 'strobe'
        self.channels[startchannel+5] = 'intensity'
        self.color_change = 0
        self.strobe = 0
        
        
        
        
        
        