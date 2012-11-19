import socket
import select
import time
from ola.OlaClient import OlaClient, Universe
from birdfish.output.base import BaseNetwork
# from birdfish.output.client_wrapper import ClientWrapper


class ClientWrapper(object):
  def __init__(self):
    self._quit = False
    self._sock = socket.socket()
    self._sock.connect(('localhost', 9010))
    self._client = OlaClient(self._sock)

  def Stop(self):
    self._quit = True

  def Client(self):
    return self._client

  def Run(self):
    while not self._quit:
      i, o, e = select.select([self._sock], [], [])
      if self._sock in i:
        self._client.SocketReady()

class OLA(BaseNetwork):

    def __init__(self,universe):
        super(OLA, self).__init__()
        self.universe = universe
        self.wrapper = ClientWrapper()
        self.client = self.wrapper.Client()

    def send_data(self):
        # print U.dmx
        self.update_data()
        try:
            def dmx_sent(state):
                self.wrapper.Stop()
            self.client.SendDmx (self.universe,self.data,dmx_sent)
            self.wrapper.Run()
        except socket.error, (value,message):
            print "Socket Error, continuing: %s" % message
            self.wrapper = ClientWrapper()
            self.client = self.wrapper.Client()
            time.sleep(.5)

    def dmx_sent(self,state=None):
        self.last_dmx = copy.copy(self.dmx)
        # not sure this is needed @@


