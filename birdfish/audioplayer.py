""" Play a WAVE file.

Looks like I need to have the player be an object that manages a thread for
playing, rather than the player BEING a threaad object itself.  This is because
for the player to respond to signals it can't start itself.  Should also better
allow for restart etc.


Also consider using subprocess instead of thread
"""

import pyaudio
import wave
import threading

chunk = 1024


class AudioPlayer(threading.Thread):
    deamon = True

    def init_play(self, wavfile):
        self.playmessage = (144, 39)
        self.wf = wf = wave.open(wavfile, 'rb')
        p = self.pyaudio
        self.paused = False
        self.stream = p.open(
                    format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)

    def __init__(self, wavfile):
        threading.Thread.__init__(self, name="audioplayer")
        self._stopevent = threading.Event()
        self.wavfile = wavfile
        self.pyaudio = pyaudio.PyAudio()
        self.init_play(wavfile)

    def run(self):
        while not self._stopevent.is_set():
            data = self.wf.readframes(chunk)
            if data != '':
                self.stream.write(data)
            else:
                self.join()

    def join(self, timeout=None):
        self._stopevent.set()
        self.stream.close()
        self.pyaudio.terminate()
        self.wf.close()
        threading.Thread.join(self, timeout)

    def stop(self):
        self.join()

    def pause(self):
        # TODO not implemented
        self.paused = True

    def trigger(self, data):
        if data:  # ignore off signal
            self.start()


class Player(object):
    def __init__(self, wavfile):
        self.wavfile = wavfile
        self.audio = None
        self.last_audio = None
        self.reset()

    def reset(self):
        # keeping a reference so the thread can join
        self.last_audio = self.audio
        self.audio = AudioPlayer(self.wavfile)

    def play(self):
        self.audio.start()
        while not self.audio._stopevent.is_set():
            pass
        self.reset()

    def trigger(self, data, **kwargs):
        if data:  # ignore off
            self.play()
