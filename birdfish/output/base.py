import array


class BaseNetwork(object):

    def __init__(self):
        # TODO - should a network have a keep alive attr?
        self.dmx_keep_alive = True
        self.elements = []
        self.data = array.array('B', ())

    def init_data(self):
        max_chan = 0
        for l in self.elements:
            for c in l.channels:
                max_chan = max(max_chan, c)
        self.data.extend([0 for i in range(max_chan)])

    def blackout(self):
        # @@ todo
        pass

    def reset(self):
        self.data = array.array('B', (0,) * len(self.data))

    def add_element(self, element):
        if element not in self.elements:
            self.elements.append(element.device)
            return True
        return False
        # TODO element.network=self? will this ever be needed?

    def remove_element(self, element):
        try:
            self.elements.remove(element)
            return True
        except ValueError:
            return False

    def get_named_element(self, name):
        for l in self.elements:
            # @@ should this be case insensitive?
            if l.name.lower() == name.lower():
                return l
        return False

    def add_elements(self, lights):
        for l in lights:
            self.add_element(l)

    def update_data(self):
        [e.update_data(self.data) for e in self.elements]

    def send_data(self):
        raise NotImplementedError


class DefaultNetwork(BaseNetwork):
    def __init__(self):
        super(DefaultNetwork, self).__init__()

    def send_data(self):
        # this class sends no data, only manages higher level objects
        pass
