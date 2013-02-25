#!/usr/bin/env python

from collections import defaultdict
import sys
from OSC import OSCServer
import time
import threading


def my_handler(addr, tags, data, client_address):
    print addr, data, client_address


class OSCServerThread(OSCServer):
    def start(self):
        self._server_thread = threading.Thread(target=self.serve_forever)
        self._server_thread.setDaemon(True)
        self._server_thread.start()

    def stop(self):
        self.running = False
        self._server_thread.join()
        self.server_close()


class OSCDispatcher(OSCServer):
    def __init__(self, *args, **kwargs):
        OSCServer.__init__(self, *args, **kwargs)
        self.observers = defaultdict(list)
        self.addMsgHandler('default', self.dispatch)

    def add_observer(self, message_key, recv, type='trigger'):
        self.observers[message_key].append({'receiver': recv, 'type': type})

    def add_trigger(self, message_key, recv):
        self.observers[message_key].append({
            'type': 'trigger',
            'receiver': recv,
            })

    def add_map(self, message_key, recv, attribute, in_range=(0, 1),
            out_range=(0, 1), data_member=0):
        # TODO use namedtuple instead of dict
        self.observers[message_key].append({
            'type': 'map',
            'receiver': recv,
            'in_range': in_range,
            'out_range': out_range,
            'attribute': attribute,
            'data_member': data_member,
            })

    def remove_observer(self, element):
        for message in self.observers:
            self.observers[message] = \
                [x for x in self.observers[message] if x[0] != element]

    def dispatch(self, addr, tags, data, client_address):
        if not "accxyz" in addr:
            print addr, data, client_address
        message_key = addr
        if message_key in self.observers:
            for destination in self.observers[message_key]:
                if destination['type'] == 'trigger':
                    # trigger type
                    vel = data[0]
                    destination['receiver'].trigger(vel, key=message_key)
                elif destination['type'] == 'map':
                    in_value = data[destination['data_member']]
                    if not (destination['in_range'][0] <= in_value
                            <= destination['in_range'][1]):
                        # input value out of range
                        continue
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

    def start(self):
        self._server_thread = threading.Thread(target=self.serve_forever)
        self._server_thread.setDaemon(True)
        self._server_thread.start()

    def stop(self):
        self.running = False
        self._server_thread.join()
        self.server_close()

if __name__ == '__main__':
    # s = OSCServer(('0.0.0.0',8000))
    s = OSCServerThread(('0.0.0.0', 8000))
    s.addMsgHandler('default', my_handler)
    # s.serve_forever()
    # s.run = True
    s.start()
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            s.stop()
            sys.exit()
