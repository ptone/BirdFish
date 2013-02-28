import tuio

from birdfish.input.base import BaseDispatcher


class TuioDispatcher(BaseDispatcher):

    def __init__(self, *args, **kwargs):
        super(TuioDispatcher, self).__init__(*args, **kwargs)
        self.tracking = tuio.Tracking()
        self.assignments = {}
        self.bound_objects = set()
        self.bindings = {}
        self.last_cursors = set()

    def add_assignment(self, object, xpos='', ypos='',
            in_range=(0, 1), xout_range=(0, 1), yout_range=(0, 1)):
        if object not in self.assignments:
            self.assignments[object] = {
                    'xpos': xpos,
                    'ypos': ypos,
                    'xout_range': xout_range,
                    'yout_range': yout_range,
                    }

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

    def get_val_for_range(self, val, r, invert=True):
        val = r[0] + (val * (r[1] - r[0]))
        if invert:
            return r[1] - val
        else:
            return val

    def update(self):
        self.tracking.update()
        cursors = set(self.tracking.profiles['/tuio/2Dcur'].sessions)
        removed_cursors = self.last_cursors - cursors
        if removed_cursors:
            print 'removed: ', removed_cursors
        added_cursors = cursors - self.last_cursors
        for cur in removed_cursors:
            if cur in self.bindings:
                obj = self.bindings[cur]
                self.bound_objects.remove(obj)
                del(self.bindings[cur])
                obj.trigger(0)
        if added_cursors:
            # TODO or if len cursors > bindings < assignments?
            print 'added: ', added_cursors
            print self.last_cursors, cursors
            unbound_objects = (set([obj for obj in self.assignments.keys()]) -
                    self.bound_objects)
            for cur, obj in zip(added_cursors, unbound_objects):
                self.bindings[cur] = obj
                self.bound_objects.add(obj)
                obj.trigger(1)
        self.last_cursors = cursors

        for c in self.tracking.cursors():
            if c.sessionid in self.bindings:
                obj = self.bindings[c.sessionid]
                assignment = self.assignments[obj]
                xval = self.get_val_for_range(c.xpos, assignment['xout_range'])
                print assignment['xpos']
                setattr(obj, assignment['xpos'], xval)
                yval = self.get_val_for_range(c.ypos, assignment['yout_range'])
                setattr(obj, assignment['ypos'], yval)
                print 'cursor ', c.sessionid, obj.name, xval, yval

    def cleanup(self):
        self.tracking.stop()
