============
Introduction
============

Birdfish is a software package to allow you to programatically control lighting 
used for displays or theater.  The features provide a way to abstract the 
complexities of high channel counts and varying protocols used by the
electronics to control the lights.

The existing software this aims to provide an alternative to typically represents each
channel as a row, and slices time into a number of discreet chunks resulting in
a grid or matrix, where each box represents the intensity value of that slice
of time.  There are two problems with this approach that this software attempts
to solve. The first is that with ever increasing channel counts, and lights
that use multiple channels, it gets very tedious to fill in each block of the
grid, even with helper tools.  Second, modifications to the display or to the
sequence result in completely reworking the channel values to result in the
desired changes.

Light Elements instead of channels
----------------------------------

A LightElement is the fundamental building block object in Birdfish.  It its
most basic form, it is a single channel on a dimmer/controller.  But even in
this basic form, it offers some powerful features.  Because a LightElement is
a object in software, it can have attributes that you can set.  For an RGB
light, a LightElement would wrap the three channels into one object.

Events control LightElements
----------------------------

Events are the things that happen at a specific time to control a LightElement.

There are two types of events:

Trigger Events
    These are a trigger of Element intensity, anything over 0 is an "on" trigger,
    while a trigger with value 0 is an "off" trigger.

Mapped Events
    These events change the value of some attribute of a LightElement over
    time. For example, you might use the numbers 1-9 on the keyboard to map how
    fast a light might strobe, or connect a MIDI controller knob to the color
    of a light.

Birdfish takes events and renders them into channel output
----------------------------------------------------------

Birdfish takes a sequence of events, either pre-recorded or live, and uses them
to trigger LightElements, which then, based on their attributes, will generate
channel data over time.

Lets work with an example.  A basic LightElement supports an attribute called
"attack".  The value of this attribute is the number of seconds it takes
a light to dim up from black to full intensity when it is triggered on.  In
grid based software, this might be represented as a ramp of increasing height
from left to right. In Birdfish, it is simply a property of the LightElement.
A single trigger event will cause the LightElement to start outputting first
low values, and gradually brighter values over time until full intensity is
reached until an off trigger event is received. 

Now a sequence of several minutes might have dozens of these trigger events. If
at a later time, you want to change the attack of a given light, you simply go
to where that LightElement is defined, and give it a different attack value. No
changes need to be made to the sequence because the timing of the triggers is
all still OK. When the sequence plays again, Birdfish will once again trigger
the LightElement, but now the LightElement will render its channel output
differently, using the new attack value. 

This is just scratching the surface of what this separation between event and
output can yield.  Also because we are defining our lights in code, you can use
a variable for attack, and share it between multiple LightElements.  And
because more than one LightElement can use the same channels, you can have one
that has a long attack value, and another that has none, and trigger the one
you want as needed in the sequence, or use map events to change the value for
different parts of the sequence.

Groups, Chases, and Effects
---------------------------

LightElement is the base object in an inheritance tree (class tree). RGBLight
is one that adds features for RGB, such as having a hue attribute that
automatically adjusts the R,G,and B channels to match a color of a certain Hue
in HSV colorspace (colorwheel).

In addition to derived classes for certain light types, there are also Groups
and Chases.  A group is simply a container object containing a bunch of other
LightElements. These can be nested so you can have groups like:

north_window is the name of a LightElement that represents a string of red lights
around a particular window. You might combine this with other LightElements
into the following groups:

- window_group
- red_lights

An all_house group might consist of [window_group, roof_group]

When a group is triggered, the software automatically triggers all its
elements.  If a group contains other groups, this trigger is propogated down to
each light element that generates channel output.

A chase is a group that when triggered, will trigger each element in series
over time. A chase has a number of attributes that control how those lights
chase.  What is recorded in the sequence is just the timing of the trigger, the
complexity of the chase is all generated in software.



