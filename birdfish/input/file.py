import threading
import time
import os
import datetime
import csv
from operator import itemgetter


class EventReader(threading.Thread):
    def __init__(self,file=None,show=None):
        threading.Thread.__init__(self, name="event file player")
        if not file:
            raise ValueError("no file path provided")
        self.file = file
        self.show = show
        self._stopevent = threading.Event()
        self.pending_event = None
        self.started = 0
        self.start_offset = 0
        self.song_start = "start"
        self.looping = False
        self.looping_duration = 0
        self.run_started = 0
        self.reader = None
        self.init_reader()

    def init_reader(self):
        del(self.reader)
        self.reader = csv.reader(open(self.file,'rb'))

    def seek_start(self):
        while not self.started:
            event = self.reader.next()
            m = event[1]
            if m == self.song_start:
                self.start_offset = float(event[3]) #ms timestamp of event
                self.started = time.time()
                if hasattr(self.show, 'audio_player'):
                    self.show.audio_player.start()
                print self.start_offset

    def run(self):
        print "%s starts" % (self.getName(),)
        #TODO self.run_started and self.started seem redundant and may not be needed?
        self.run_started = time.time()
        self.seek_start()
        while not self._stopevent.is_set():
            # @@ do I need an attribute here to only run full loops - or always respect duration?
            if self.looping and self.looping_duration:
                if time.time() > self.run_started + self.looping_duration:
                    self._stopevent.set()
                    continue
            if not self.pending_event:
                try:
                    self.pending_event = self.reader.next()
                    print self.pending_event
                except StopIteration:
                    if self.looping:
                        if self.looping_duration:
                            if time.time() > self.run_started + self.looping_duration:
                                self._stopevent.set()
                                continue
                        self.init_reader()
                        self.started = 0
                        self.seek_start()
                        print "looping"
                        continue
                    else:
                        self._stopevent.set()
                        continue
                    self._stopevent.set()
                    continue
            # tracktime = (((time.time() - self.started)) + self.start_offset)
            time_delta = time.time() - self.started
            event_delta = float(self.pending_event[3]) - self.start_offset
            if time_delta >= event_delta:
                if self.pending_event[0][0].lower() == 't':
                    print "triggering " + self.pending_event[1]
                    lightobj = self.show.get_named_element(self.pending_event[1])
                    lightobj.trigger(int(self.pending_event[2]))
                elif self.pending_event[0][0].lower() == 'm':
                    lightname, attr = self.pending_event[1].split('.')
                    lightobj = self.show.get_named_element(lightname)
                    setattr(lightobj,attr,int(self.pending_event[2]))
                self.pending_event = None
            else:
                self._stopevent.wait(.1)
        print "%s ends" % (self.getName(),)
        self.cleanup()



    def cleanup(self):
        if self.file:
            try:
                self.file_obj.close()
            except:
                pass
                
    def join (self,timeout=None):
        if self.looping:
            self._stopevent.set()
            self.cleanup()
        threading.Thread.join(self, timeout)

    def stop(self):
        self._stopevent.set()
        self.cleanup()
        self.join()

def logger(s):
    print s
    
class TriggerFilePlayer(threading.Thread):
    observers = {}
    daemon = True
    
    
    def __init__(self,file, dispatch_func=logger):
        threading.Thread.__init__(self, name="trigger file player")
        self._stopevent = threading.Event()
        self.file = file
        self.file_obj = open(file,'r')
        self.dispatch = dispatch_func
        self.pending_message = None
        self.started = 0
        self.start_offset = 0
        self.song_start = [144, 39, 127, 0]
        self.looping = False
        self.looping_duration = 0
        self.run_started = 0
    
    def init_reader(self):
        self.file_obj = open(self.file,'r')
    
    def seek_start(self):
        while not self.started:
            l = self.file_obj.readline().strip()
            event = eval(l)
            m = event[0]
            if m == self.song_start:
                self.start_offset = event[1]#ms timestamp of event
                self.started = time.time() 
        
    def run(self):
        print "%s starts" % (self.getName(),)
        self.run_started = time.time()
        self.seek_start()
        while not self._stopevent.is_set():
            # @@ do I need an attribute here to only run full loops - or always respect duration?
            if self.looping and self.looping_duration:
                if time.time() > self.run_started + self.looping_duration:
                    self._stopevent.set()
                    continue
            if not self.pending_message:
                l = self.file_obj.readline().strip()
                if l:
                    self.pending_message = eval(l)
                else:
                    self.cleanup()
                    if self.looping:
                        if self.looping_duration:
                            if time.time() > self.run_started + self.looping_duration:
                                self._stopevent.set()
                                continue
                        self.init_reader()
                        self.started = 0
                        self.seek_start()
                        print "looping"
                        continue
                    else:
                        self._stopevent.set()
                        continue
            tracktime = (((time.time() - self.started) * 1000) + self.start_offset)
            if tracktime >= self.pending_message[1]:
                self.dispatch(self.pending_message)
                self.pending_message = None
            self._stopevent.wait(.003)
        print "%s ends" % (self.getName(),)
        self.cleanup()



    def cleanup(self):
        if self.file:
            try:
                self.file_obj.close()
            except:
                pass
                
    def join (self,timeout=None):
        if self.looping:
            self._stopevent.set()
            self.cleanup()
        threading.Thread.join(self, timeout)

    def stop(self):
        self._stopevent.set()
        self.cleanup()
        self.join()

class BasicScheduleComponent(object):
    def __init__(self, *arg, **kwargs):
        super(BasicScheduleComponent, self).__init__()
        self.file = kwargs.get('file','')
        self.looping_duration = 0
        self.looping = False
        self.timed = False
        self.name = "generic component"
        
        
    def time_test(self):
        return datetime.datetime.now().minute % 10
        
class BasicScheduledPlayer(threading.Thread):
    """A simple manager of trigger file playing will need something more put together later @@"""
    def __init__(self, *arg, **kwargs):
        super(BasicScheduledPlayer, self).__init__()
        self._stopevent = threading.Event()
        self.dispatch = kwargs.get('dispatch_func')
        # (tm_year=2010, tm_mon=12, tm_mday=3, tm_hour=4, tm_min=51, tm_sec=4, tm_wday=4, tm_yday=337, tm_isdst=0)
        self.start_time = datetime.time()
        self.end_time = datetime.time()
        self.components = []
        self.show = None
    
    def run(self):
        print "Scheduled Player Starts"
        while not self._stopevent.is_set():
            now = datetime.datetime.now().time()
            if not (self.start_time < now < self.end_time):
                print "delaying"
                if self.show:
                    self.show.blackout()
                time.sleep(1)
                continue
            for c in self.components:
                t = TriggerFilePlayer(c.file,dispatch_func=self.dispatch)
                t.looping_duration = c.looping_duration
                t.looping = c.looping
                print "starting %s" % c.name
                t.start()
                if c.timed:
                    while c.time_test():
                        time.sleep(1)
                    print "%s time test returned false" % c.name
                    t.stop()
                else:
                    t.join()
                    print "%s ended" % c.name
    
    def stop(self):
        self._stopevent.set()
        self.join()

class FileMerger(object):
    def __init__(self):
        super(FileMerger, self).__init__()
        self.all_events = []

    def merge_files(self,filelist, outfile=None):
        for f in filelist:
            self.add_file(f)
        self.merge()
        if self.outfile:
            self.write_file(outfile)

    def write_file(self,outfile):
        fobj = open(outfile,'wb')
        writer = csv.writer(fobj)
        for e in self.sorted_events:
            writer.writerow(e)
        fobj.close()

    def merge(self):
        """Sort the concatenated data"""
        self.sorted_events = sorted(self.all_events, key=itemgetter(3))
        self.sorted_events.insert(0,['trigger','start','255','0'])

    def add_file(self,f):
        # ('type','target','data','time'))
        reader = csv.reader(open(f,'rb'))
        in_start = False
        start_time = 0
        for l in reader:
            if not in_start and l[1].lower() != 'music':
                start_time = l[3]
                continue
            # align all time to start start
            l[3] = l[3] - start_time
            self.all_events.append(l)

