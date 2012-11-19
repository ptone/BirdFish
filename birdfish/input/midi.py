import pyportmidi as pypm
import Queue
import threading
import os

class MidiReader(threading.Thread):
    # @@ note can't this be rolled into the dispatcher?
    # the reason not is that sending signals may take time, and want to keep reader focused on taking
    # messages in from midi.
    # but couldn't midi messages buffer in the midi buffer instead of the queue between the 
    # reader and dispatcher - hmmm
    working = True

    def __init__(self,device, queue):
        threading.Thread.__init__(self, name="midireader")
        pypm.init()
        self._input = pypm.Input(device)
        self._stopevent = threading.Event()
        self._sleepperiod = 1.0
        self._queue = queue

    def run(self):
         """
         overload of threading.thread.run()
         main control loop
         """
         print "%s starts" % (self.getName(),)

         count = 0
         while not self._stopevent.is_set():
             if self._input.poll():
                 d = self._input.read(12)
                 # print d
                 self._queue.put(d)
                 # put it into a pipe or queue
             self._stopevent.wait(.1)
         print "%s ends" % (self.getName(),)


    def join (self,timeout=None):
        self._stopevent.set()
        pypm.quit()
        threading.Thread.join(self, timeout)


    def stop(self):
        self.join()

class MessageDispatcher(threading.Thread):
# @@ this class is redundant right?
    observers = {}
    daemon = True

    def __init__(self, queue):
        threading.Thread.__init__(self, name="dispatcher")
        self._queue = queue
        self._stopevent = threading.Event()
        self.logger = None

    def add_observer(self,message_key,recv,type='trigger'):
        if message_key in self.observers:
            self.observers[message_key].append((recv,type))
        else:
            self.observers[message_key] = [(recv,type)]

    def dispatch(self,message):
        """take a midi message and dispatch it to object who are interested"""
        message_key = tuple(message[0][:2])
        if message_key in self.observers:
            for recv,type in self.observers[message_key]:
                if type[0].lower() == 't':
                   # trigger type
                   vel = message[0][2]
                   recv.trigger(vel * 2)
                elif type[0].lower() == 'm':
                   message_data = message[0][2:]
                   recv.map(message_data)
                # @@ does reciever need original message?
                recv.signal(message)
        else:
            # @@ debug log undispatched signals
            print message
            pass

    def run(self):
        while not self._stopevent.is_set():
            d = self._queue.get()
            for m in d:
                self.dispatch(m)
            self._queue.task_done()

    def join (self,timeout=None):
        self._stopevent.set()
        threading.Thread.join(self, timeout)

class MidiDispatcher(threading.Thread):
    daemon = True

    def __init__(self,device):
        threading.Thread.__init__(self, name="dispatcher")
        pypm.init()
        self._input = pypm.Input(device)
        self._stopevent = threading.Event()
        self._sleepperiod = 1.0
        self.file = None
        self.file_obj = None
        self.logger = None
        self.observers = {}


    def add_observer(self,message_key,recv,type='trigger'):
        # @@ could just store first letter of type and simplify the look up end
        if message_key in self.observers:
            self.observers[message_key].append((recv,type))
        else:
            self.observers[message_key] = [(recv,type)]

    def remove_observer(self, element):
        for message in self.observers:
            self.observers[message] = \
            [x for x in self.observers[message] if x[0] != element]

    def dispatch(self, message):
        """take a midi message and dispatch it to object who are interested"""
        message_key = tuple(message[0][:2])
        if message_key in self.observers:
            for recv,type in self.observers[message_key]:
                if type[0].lower() == 't':
                   # trigger type
                   vel = data = message[0][2] * 2
                   recv.trigger(vel, key=message_key)
                   if self.logger:
                       self.logger.log_event(recv,type,data)
                elif type[0].lower() == 'm':
                   # map data - recv is tuple of lightobj and attr list
                    message_data = data = message[0][2:]
                    lightobj,attributes = recv
                    for i, d in enumerate(message_data):
                        # print "len"
                        # print i, len(attributes)-1, d
                        if i <= (len(attributes)-1):
                            # print "i in range"
                            # print d
                            if d:
                                # print "data OK"
                                # or data change
                                # @@ note that attr map changed from 0-1 to 0-255
                                setattr(lightobj,attributes[i], d * 2)
                                # print "attribute %s set to %s" % (attributes[i], d/127.0)
                                if self.logger:
                                    self.logger.log_event(lightobj,type,d * 2, attr=attributes[i])
        else:
            # @@ debug log undispatched signals
            print message
            pass

    def run(self):
        print "%s starts" % (self.getName(),)
        if self.file:
            i = 1
            base, ext = os.path.splitext(self.file)
            while os.path.exists(self.file):
                self.file = "%s-%s%s" % (base,i,ext)
                i += 1
                # raise ValueError("output file exists")
            f = self.file_obj = open(self.file,'w')
        count = 0
        while not self._stopevent.is_set():
            if self._input.poll():
                d = self._input.read(12)
                for m in d:
                    self.dispatch(m)
                    if self.file:
                        # @@ currently can not set file after dispatcher 
                        # started - would be nice to
                        # could also use start trigger?
                        # The entire file function needs to be replaced.
                        # one approach would be to have a "universal" reciever
                        # which would get every dispatch from every input plugin
                        # the challenge will be to sync the midi clock
                        f.write(str(m) + '\n')
                # print d
                # put it into a pipe or queue
            self._stopevent.wait(.1)
        print "%s ends" % (self.getName(),)



    def join (self,timeout=None):
        self._stopevent.set()
        pypm.quit()
        if self.file:
            try:
                self.file_obj.close()
            except:
                pass
        threading.Thread.join(self, timeout)

    def stop(self):
        self.join()
