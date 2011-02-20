Notes on installing portmidi with pyportmidi
============================================

http://sourceforge.net/projects/portmedia/files/portmidi/

install portmidi using cmake and instructions in pm_mac subfolder

this puts libs in ``/usr/local``

Use current version of pyport midi included with portmidi in pm_python subfolder

Need to first create dummy files wanted by setup.py::

    touch CHANGES.txt
    touch TODO.txt


have cython installed either at system site-packages, or in virtualenv then::

    python setup.py build
    python setup.py install


Need to edit __init__ file in pyportmidi from::

    from .midi import *

to::

    from midi import *

