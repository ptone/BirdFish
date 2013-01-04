from lumos.source import DMXSource
from birdfish.output.base import BaseNetwork

class LumosNetwork(BaseNetwork):

    def __init__(self, universe):
        super(LumosNetwork, self).__init__()
        self.universe = universe
        self.client = DMXSource(universe=universe)

    def send_data(self):
        # TODO this doesn't seem the most efficient
        # but the only way to get "brightest element wins"
        # rendering that I could come up with
        self.reset()
        self.update_data()
        self.client.send_data(self.data)
        # print self.data
