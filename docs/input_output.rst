================
Input and Output
================

Birdfish provides a toolset to convert time based events, into light signalling
output. This can be considered a core rendering engine that only knows about
events in, and channel data out. While the channel values are assumed to be in
the range 0-255. However nothing about Birdfish's core assumes anything about
what is generating the events, or where the channel data is being sent.  This
is handled by a choice of input and output modules.  At this point, the number
of options are relatively limited, but here is a list of what is planned:

Inputs
------

 * PC Keyboard *
 * MIDI (file or live input) **
 * Event File (A Birdfish specific format for recording events)
 * OSC (Open Sound Control) *
 * Kinect **
 * Touch Devices **
 * Web Console *

Outputs
-------

 * `OLA DMX <http://www.opendmx.net/index.php/OLA>`_ (E1.31, USB) 
 * PixelNet *
 * Renard *
 * LOR *
 * Event File **
 * Vixen File *
 * DMX USB (pure python) *
 * E1.31 (pure python) *

_   * not yet implemented
_  ** partially implemented
