================
Input and Output
================

Birdfish provides a toolset to convert time based events, into light signalling
output. This can be considered a core rendering engine that only knows about
events in, and channel data out. Nothing about Birdfish's core assumes anything
about what is generating the events, or where the channel data is being sent
to.  This is handled by a choice of one or more input and output modules.  At
this point, the number of options are relatively limited, but here is a list of
what is planned:

Inputs
------

 * MIDI signals
 * OSC (Open Sound Control)
 * Event File (A Birdfish specific format for recording events)
 * Web (using realtime websockets) **
 * MIDI file *
 * PC Keyboard (currently handled by virtual midi keyboards)*
 * Kinect **

Outputs
-------

 * E1.31 (pure Python via Lumos Library)
 * `OLA DMX <http://www.opendmx.net/index.php/OLA>`_ (E1.31, USB) 
 * PixelNet *
 * Event File **
 * One or more sequence software formats *
 * Renard, LOR (low priority)*

_   * not yet implemented
_  ** partially implemented
