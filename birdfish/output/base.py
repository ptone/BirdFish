import array

class BaseNetwork(object):

    def __init__(self):
        self.elements = []
        self.data = array.array('B',())

    def init_data(self):
        max_chan = 0
        for l in self.elements:
            for c in l.channels:
                max_chan = max(max_chan, c)
        self.data.extend([0 for i in range(max_chan)])

    def blackout(self):
        # @@ todo
        pass


    def update(self,show):
        for e in self.elements:
            e.update(show)

    def add_element(self, element):
        if element not in self.elements:
            self.elements.append(element)
            return True
        return False
        # element.network=self? will this ever be needed?

    def get_named_element(self,name):
        for l in self.elements:
            # @@ should this be case insensitive?
            if l.name.lower() == name.lower():
                return l
        return False

    def add_elements(self,lights):
        for l in lights:
            self.add_element(l)


    def update_data(self):
        for e in self.elements:
            e.update_data(self.data)

    def send_data(self):
        raise NotImplementedError

class DefaultNetwork(BaseNetwork):
    def __init__(self):
        super(DefaultNetwork, self).__init__()

    def send_data(self):
        # this class sends no data, only manages higher level objects
        pass
