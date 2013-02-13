Installation
============

Currently in this alpha release, the the best supported configuration OS
X, though those experienced with Linux should also be able to get going by
tweaking these directions. Both Linux and Win32 platforms will be fully supported in the future.

If you are at all experienced with Python development, you should use the
`virtualenv <http://pypi.python.org/pypi/virtualenv>`_ model of segregating
your Python environments. If you're only plans are to install and experiment
with this software, it is reasonable to just install onto your base system.

On OS X, ensure that your environment has a couple tools in place:

    * The latest xcode from Apple (free in app store) or `Developer tools CLI
      install
      <https://developer.apple.com/downloads/index.action?=command%20line%20tools>`_
      (requires Apple developer ID)
    * `Homebrew <http://mxcl.github.com/homebrew/>`_
    * git (for getting latest development version) **brew install git**
    * portmidi for midi control **brew install portmidi**

These are my recommended steps for getting your Python environment setup - you
will need your password to install some tools globally (type them into
terminal)::

    cd /tmp
    curl -O http://python-distribute.org/distribute_setup.py
    sudo python distribute_setup.py
    curl -O https://raw.github.com/pypa/pip/master/contrib/get-pip.py
    sudo python get-pip.py
    sudo pip install -U virtualenv
    sudo pip install -U virtualenvwrapper

To finish the installation of the virtualenv wrapper tool, you will need to add
these three lines to your .bashrc file in the root of your home folder.::

    export WORKON_HOME=$HOME/.virtualenvs
    export PROJECT_HOME=$HOME/Devel
    source /usr/local/bin/virtualenvwrapper.sh

Now you need to make a Python virtualenvironment to execute the BirdFish code::

    mkvirtualenv birdfish
    pip install -e git+git@github.com:ptone/BirdFish.git#egg=birdfish-dev
    pip install -e git+git@github.com:ptone/protomidi.git#egg=protomidi-dev
    pip install -e git+git@github.com:ptone/Lumos.git#egg=lumos-dev
    pip install -e git+https://github.com/ptone/pyosc.git#egg=pyOSC-dev

BirdFish is the main control software package, protomidi is the Python bindings
to the PortMidi library which makes your system's Midi infrastructure
available, and Lumos is a library for sending E1.31. pyOSC is a Python
implementation of the OSC command protocol.

Download a small virtual midi keyboard called `MidiKeys
<http://www.manyetas.com/creed/midikeys.html>`_

If you want to use DMX USB hardware and not just E1.31 - you will need to
install OLA, more information can be found on its `home page
<http://www.opendmx.net/index.php/Open_Lighting_Architecture>`_. You need to
make sure that the Python bindings are part of the binary - last I checked,
this was not the case, so you need to build from source.

Anytime you want to execute you need to "activate" the BirdFish Python
environment in a terminal session. Just type::

    workon birdfish

You should then see (birdfish) in your shell prompt.

To open the examples (note you need Midikeys open)::

    cdvirtualenv
    cd birdfish/examples
    python <example name>

To update to the latest development version of BirdFish::

    cdvirtualenv
    cd birdfish
    git pull
