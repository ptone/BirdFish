import time
from pandac.PandaModules import *
from pandac.PandaModules import Material
from pandac.PandaModules import VBase4
import threading
import Queue
import os
import select

dmx_q = Queue.Queue()

class PipeReader(threading.Thread):
    """docstring for PipeReader"""
    daemon = True
    def __init__(self):
        self._stopevent = threading.Event()
        self.daemon = True
        threading.Thread.__init__(self, name="dmxreader")
    
    def run(self):
        """
        overload of threading.thread.run()
        main control loop
        """
        print "%s starts" % (self.getName(),)

        count = 0
        if not os.path.exists('/tmp/dmxpipe'): #@@ and type pipe
            os.mkfifo('/tmp/dmxpipe')
        
        # while not self._stopevent.is_set():
        f = open('/tmp/dmxpipe','rb',0)
        data_buffer = ''
        while True: # or test for inputs
            readable, writable, ioerr = select.select ([f],[],[])
            # @@ need to limit to a preset 512 bytes to deal with read/write timing?
            # or maybe the queue object will stack those up...
            # need to grab this from readable to be proper - but I only have one input
            data = f.read() # this blocks - or should?
            if len(data) == 0:
                # can cause broken pipes to close this when othe process expecting to write to it
                pass
                # f.close()
                # f = open('/tmp/dmxpipe','rb',0)
                # continue
            data_buffer += data
            while len(data_buffer) >= 512:
                # f.close()
                # print "len self.buffer in while %s" % len(data_buffer)
                buffer_chunk = data_buffer[:512]
                data_buffer = data_buffer[512:]
                dmx_q.put(buffer_chunk)
                #print buffer_chunk
            else:
                pass
                # print "len self.buffer out while %s" % len(data_buffer)
                # time.sleep(.015)
                # print "no data"
            # time.sleep(.5)
        print "%s ends" % (self.getName(),)

            
    def join (self,timeout=None):
        self._stopevent.set()
        threading.Thread.join(self, timeout)
        
    def stop(self):
        self.join()
        
class LightViewer(object):
    
    def __init__(self, color=(1,1,1), channels=(1,), pos=(0, 20, 0)):
        self.color = color
        # if channel given as int  - make tuple @@
        self.channels = channels
        self.pos = pos
        self.add_material()
        self.add_model()
        
    def add_material(self):
        new_material = Material()
        new_material.setEmission(VBase4(*self.color + (1,)))
        new_material.setAmbient(VBase4(0,0,0,0))
        new_material.setDiffuse(VBase4(0,0,0,0))
        self.material = new_material

    def add_model(self):
        model = loader.loadModel("misc/sphere")
        model.setMaterial(self.material)
        model.setScale(1, 1, 1)
        model.setPos(*self.pos)
        model.reparentTo(render)
        # model.originalcolor = color
        self.model = model
    
    def update(self,dmx):
        dmx_val = dmx[self.channels[0]  - 1 ] # @@ dmx 1 based index
        intensity = dmx_val/255.0
        self.material.setEmission(VBase4(intensity,intensity,intensity,1))
        
class PandaViewer(object):
    """docstring for PandaViewer"""
    def __init__(self):
        super(PandaViewer, self).__init__()
        import direct.directbase.DirectStart

        self.lights = []
        # 
        # plight = PointLight('plight')
        # plight.setColor(VBase4(0.2, 0.2, 0.2, 1))
        # plnp = render.attachNewNode(plight)
        # plnp.setPos(10, 20, 0)
        # render.setLight(plnp)

        base.setBackgroundColor(0, 0, 0)

        # self.m = self.material = Material()
        # self.m.setEmission(VBase4(1,1,0,1))
        # self.material.setAmbient(VBase4(0,0,0,0))
        # self.material.setDiffuse(VBase4(0,0,0,0))
        # 
        # self.s = self.spheremodel = loader.loadModel("misc/sphere")
        # self.s.setMaterial(self.m)
        # 
        # # can be reset after assigned - so does mean need a material for each model
        # self.m.setEmission(VBase4(1,1,1,1))
        # 
        # self.spheremodel.reparentTo(render)
        # 
        # self.s.setScale(2, 2, 2)
        # self.s.setPos(0, 20, 0)
        # print self.s
        # print base

        # # Load the environment model.
        # environ = loader.loadModel("models/environment")
        # # Reparent the model to render.
        # environ.reparentTo(render)
        # # Apply scale and position transforms on the model.
        # environ.setScale(0.25, 0.25, 0.25)
        # environ.setPos(-8, 42, 0)
    
    def add_light(self,lightobj):
        self.lights.append(lightobj)


    def update(self,dmx):
        for l in self.lights:
            l.update(dmx)
        
    def start(self):
        reader = PipeReader()
        reader.start()
        taskMgr.step()
        while True:
            try:
                buffer_chunk = dmx_q.get(True,.2)
                dmx_data = [ord(c) for c in buffer_chunk]
                # print dmx_data
                self.update(dmx_data)
                taskMgr.step()
            except Queue.Empty:
                taskMgr.step()
        # b = 255
        # st = time.time()
        # for i in range(40):
        #     b = b - 6
        #     self.update([b*1.7,b*1.2,b])
        #     # self.s.setMaterial(self.m)
        #     
        #     time.sleep(.025)
        # f = time.time()
        # print f - st
        # run()



def main():
    pv = PandaViewer()

    # l1 = LightViewer(channels=(1,),pos=(-3,20,0))
    # l2 = LightViewer(channels=(2,),pos=(0,20,0))
    # l3 = LightViewer(channels=(3,),pos=(3,20,0))
    # pv.add_light(l1)
    # pv.add_light(l2)
    # pv.add_light(l3)
    
    y = 1
    x = -5
    for i in range(1,17):
        l = LightViewer(channels=(i,),pos=(x,20,y))
        l.model.setScale(.25,.25,.25)
        # y += .6
        x += .6
        pv.add_light(l)
        
        
        
    pv.start()

if __name__ == '__main__':
    main()


