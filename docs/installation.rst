Installation
============

System Requirements
-------------------

Currently in this alpha release, the supported configuration is limited to OS
X 10.6. Both Linux and Win32 platforms will be supported in the future, and
will work now with additional configuration steps (see notes below)

If you are at all experience in Python development, you should use the
`virtualenv <http://pypi.python.org/pypi/virtualenv>`_ model of segregating
your Python environments. If you're only plans are to install and experiment
with this software, it is reasonable to just install onto your base system.

Install OLA
-----------

The primary output plugin for this release of Birdfish is the opensource Open
Lighting Architecture package. It has a double click installer downloadable
from it's `home page <http://www.opendmx.net/index.php/Open_Lighting_Architecture>`_.

Install OLA Python bindings
---------------------------

Unfortunately OLA does not include the Python bindings with the installer.
I have provided a separate installer for these bindings which can be downloaded
from [coming soon - for now you'll need to build from source and include python
bindings in build flags]

Installing portmidi for MIDI support
------------------------------------

Portmidi is part of the PortMedia project and a preconfigured binary installer
can be downloaded here for OS X 10.6.  It can also be downloaded and compiled
from source using :doc:`portmidinotes`. I'm working on a binary installer which
should will make this step much easier.

You will need some for of MIDI input.  If you do not have a physical MIDI
keyboard you can download a `software MIDI controller <http://www.manyetas.com/creed/midikeys.html>`_

Install Birdfish
----------------

[**note** for now the only way to install BirdFish is from GitHub, once a true
release is cut, pip installs will be available]

If you haven't already, install the birdfish python module.  This is best
accomplished by just running ``pip install birdfish``.  However if you are
offline, have the package downloaded, or just want to do it the old way you can
run ``python setup.py`` from inside the downloaded package.
