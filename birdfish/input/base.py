import threading
import os
from collections import defaultdict


class Dispatcher(object):

    def __init__(self, *args, **kwargs):
        self.file = None
        self.file_obj = None
        self.logger = None
        self.observers = defaultdict(list)


class BaseDispatcher(threading.Thread):

    daemon = True

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, name=kwargs.get('name', "dispatcher"))
        self._stopevent = threading.Event()
        self.file = None
        self.file_obj = None
        self.logger = None
        self.observers = defaultdict(list)

    def add_observer(self, message_key, recv, type='trigger'):
        self.observers[message_key].append({'receiver': recv, 'type': type})

    def add_trigger(self, message_key, recv):
        self.observers[message_key].append({
            'type': 'trigger',
            'receiver': recv,
            })

    def add_map(self, message_key, recv, attribute, in_range=(0, 1),
            out_range=(0, 1)):
        # TODO use namedtuple instead of dict
        self.observers[message_key].append({
            'type': 'map',
            'receiver': recv,
            'in_range': in_range,
            'out_range': out_range,
            'attribute': attribute,
            })

    def remove_observer(self, element):
        for message in self.observers:
            self.observers[message] = \
                [x for x in self.observers[message] if x[0] != element]

    def update(self):
        raise NotImplementedError

    def cleanup(self):
        pass
        # raise NotImplementedError

    def run(self):
        print "%s starts" % (self.getName(),)
        if self.file:
            i = 1
            base, ext = os.path.splitext(self.file)
            while os.path.exists(self.file):
                self.file = "%s-%s%s" % (base, i, ext)
                i += 1
                # raise ValueError("output file exists")
            # TODO
            # f = self.file_obj = open(self.file,'w')
        while not self._stopevent.is_set():
            self.update()
            self._stopevent.wait(.01)
        print "%s ends" % (self.getName(),)

    def join(self, timeout=None):
        self._stopevent.set()
        if self.file:
            try:
                self.file_obj.close()
            except:
                pass
        threading.Thread.join(self, timeout)

    def stop(self):
        self.join()
        self.cleanup()
