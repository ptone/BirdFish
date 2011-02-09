from base import BaseNetwork
# @@ import pyserial

class PixelNetUSB(BaseNetwork):

    def __init__(self,com_port):
        super(PixelNet,self).__init__()
