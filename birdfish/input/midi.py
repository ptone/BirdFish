from __future__ import division

from birdfish.input.base import BaseDispatcher
import protomidi.portmidi as pypm
import threading


class MidiReader(threading.Thread):
    # TODO note can't this be rolled into the dispatcher?
    # the reason not is that sending signals may take time, and want to keep
    # reader focused on taking messages in from midi.  but couldn't midi
    # messages buffer in the midi buffer instead of the queue between the
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

        while not self._stopevent.is_set():
            if self._input.recv():
                d = self._input.read(12)
                self._queue.put(d)
                # put it into a pipe or queue
            self._stopevent.wait(.1)
        print "%s ends" % (self.getName(),)

    def join(self, timeout=None):
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

    def add_observer(self, message_key, recv, type='trigger'):
        if message_key in self.observers:
            self.observers[message_key].append((recv, type))
        else:
            self.observers[message_key] = [(recv, type)]

    def dispatch(self, message):
        """take a midi message and dispatch it to object who are interested"""
        # message_key = tuple(message[0][:2])
        message_key = (message.channel, message.note)
        if message_key in self.observers:
            for recv, type in self.observers[message_key]:
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

    def join(self, timeout=None):
        self._stopevent.set()
        threading.Thread.join(self, timeout)


class MidiDispatcher(BaseDispatcher):

    def __init__(self, device, *args, **kwargs):
        self._input = pypm.Input(device)
        super(MidiDispatcher, self).__init__(*args, **kwargs)

    def dispatch(self, message):
        """take a midi message and dispatch it to object who are interested"""
        print message
        if message.type == 'pitchwheel':
            # pitchwheel(channel=0, value=5224)
            # print dir(message)
            # print message.__dict__
            return
        if message.type == 'sysex':
            # skip
            return
        if message.type == 'control_change':
            message_key = (message.channel, message.control)
        else:
            message_key = (message.channel, message.note)
        if message_key in self.observers:
            for destination in self.observers[message_key]:
                if destination['type'] == 'trigger':
                    # trigger type
                    if message.type == "note_off":
                        vel = 0
                    else:
                        vel = message.velocity / 127.0
                    destination['receiver'].trigger(vel, key=message_key)
                elif destination['type'] == 'map':
                    in_value = message.value
                    assert (destination['in_range'][0] <= in_value
                            <= destination['in_range'][1])
                    if destination['in_range'] == destination['out_range']:
                        out_value = in_value
                    else:
                        # convert to percentage:
                        p = (in_value - destination['in_range'][0]) / (
                                destination['in_range'][1]
                                - destination['in_range'][0])
                        out_value = destination['out_range'][0] + (
                                destination['out_range'][1]
                                - destination['out_range'][0]) * p
                    setattr(destination['receiver'], destination['attribute'],
                            out_value)
        else:
            # @@ debug log undispatched signals
            print message
            pass

    def update(self):
        if self._input.poll():
            d = self._input.recv()
            if d:
                self.dispatch(d)
                if self.file:
                    pass
                    # TODO
                    # @@ currently can not set file after dispatcher
                    # started - would be nice to could also use start
                    # trigger?  The entire file function needs to be
                    # replaced.  one approach would be to have
                    # a "universal" reciever which would get every dispatch
                    # from every input plugin the challenge will be to sync
                    # the midi clock
