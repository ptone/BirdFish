from __future__ import division

from collections import defaultdict
import sys
import protomidi.portmidi as pypm
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

    def __init__(self, device, queue):
        threading.Thread.__init__(self, name="midireader")
        pypm.init()
        self._input = pypm.Input(device)
        self._stopevent = threading.Event()
        self._queue = queue

    def run(self):
         """
         overload of threading.thread.run()
         main control loop
         """
         print "%s starts" % (self.getName(),)

         count = 0
         while not self._stopevent.is_set():
             if self._input.recv():
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
# TODO
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
        # message_key = tuple(message[0][:2])
        message_key = (message.channel, message.note)
        if message_key in self.observers:
            for recv,type in self.observers[message_key]:
                if type[0].lower() == 't':
                   # trigger type
                   vel = message[0][2]
                   recv.trigger(vel * 2)
                elif type[0].lower() == 'm':
                   message_data = message.value
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

    def __init__(self, device):
        threading.Thread.__init__(self, name="dispatcher")
        self._input = pypm.Input(device)
        self._stopevent = threading.Event()
        self.file = None
        self.file_obj = None
        self.logger = None
        self.observers = defaultdict(list)



    def add_observer(self, message_key, recv, type='trigger'):
        self.observers[message_key].append({'receiver':recv, 'type':type})

    def add_trigger(self, message_key, recv):
        self.observers[message_key].append({
            'type':'trigger',
            'receiver':recv,
            })

    def add_map(self, message_key, recv, attribute, in_range=(0, 1), out_range=(0, 1)):
        # TODO use namedtuple instead of dict
        self.observers[message_key].append({
            'type':'map',
            'receiver':recv,
            'in_range':in_range,
            'out_range':out_range,
            'attribute': attribute,
            })

    def remove_observer(self, element):
        for message in self.observers:
            self.observers[message] = \
            [x for x in self.observers[message] if x[0] != element]

    def dispatch(self, message):
        """take a midi message and dispatch it to object who are interested"""
        print message
        if message.type == 'control_change':
            message_key = (message.channel, message.control)
        else:
            message_key = (message.channel, message.note)
        if message_key in self.observers:
            for destination in self.observers[message_key]:
                if destination['type'] == 'trigger':
                   # trigger type
                   vel = data = message.velocity / 127.0
                   destination['receiver'].trigger(vel, key=message_key)
                elif destination['type'] == 'map':
                    in_value = message.value
                    assert (destination['in_range'][0] <= in_value <= destination['in_range'][1])
                    if destination['in_range'] == destination['out_range']:
                        out_value = in_value
                    else:
                        # convert to percentage:
                        p = (in_value - destination['in_range'][0])/(
                                destination['in_range'][1]
                                - destination['in_range'][0])
                        out_value = destination['out_range'][0] + (
                                destination['out_range'][1]
                                - destination['out_range'][0]) * p
                    setattr(destination['receiver'], destination['attribute'], out_value)
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
                d = self._input.recv()
                if d:
                    self.dispatch(d)
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

            # count += 1
            # heartbeat prints dot
            # if not count % 10:
                # sys.stdout.write('.')
                # sys.stdout.flush()

            self._stopevent.wait(.02)
        print "%s ends" % (self.getName(),)



    def join (self,timeout=None):
        self._stopevent.set()
        # pypm.quit()
        if self.file:
            try:
                self.file_obj.close()
            except:
                pass
        threading.Thread.join(self, timeout)

    def stop(self):
        self.join()
