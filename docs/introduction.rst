============
Introduction
============

BirdFish is a tool to programatically and interactively control the behavior of
lights or animatronics for the purpose of entertainment.

The overall design goal is to allow the person with the creative idea, to focus
more on the process of designing the way the lights behave at a high level, and
less about how to generate the timing required by the lighting control
hardware. Currently BirdFish is still for the technically inclined, and is more
about making really hard things possible than making standard stuff easy.

The features provide a way to abstract the complexities of the high channel
counts and varying protocols used by the electronics hardware that control the
lights.

The this provides an alternative to the status-quo of software which typically
represents each channel as a row, or set of collapsed rows, and slices time
into a number of discreet chunks resulting in a grid or matrix, where each box
represents the intensity value of that channel or group for that slice of time.

There are two problems with that approach which this software attempts to
solve.  The first is that with ever increasing channel counts, and lights that
use multiple channels, it gets very tedious to fill in each block of the grid,
even with helper tools.  Second, modifications to the display arrangement or to
the sequence result in completely reworking the channel values to effect the
desired changes.

The Components of BirdFish
--------------------------

BirdFish consists of a set of Elements, combined with control inputs,
connected to output networks, combined form a show.

An Element is the fundamental building block of a show in Birdfish.  In its
most basic form, it is a single channel on a dimmer/controller.  But even in
this basic form, it offers some powerful features.  Because a element is
a object in software, it can have attributes that you can set or modify, or
that can be programmed to change over time.

For an RGB light, an element wraps the three channels into one object. Chaning
that light's "hue" attribute would automatically adjust the three RGB channels
as needed.

Light Elements can be combined and nested in ways to create more complex
elements. Many single lights can be combined into groups or chases, chases
themselves can be grouped into other chases in a way that can provide for very
complex effects, without worrying about how the low level channel data is
generated.

Events control Light Elements
-----------------------------

Events are the things that happen at a specific time to control an element. You
can think of these roughly as the nubs on a music box wheel, or the notches in
a player piano sheet.

.. image:: /images/concepts.png

There are two types of events:

Trigger Events
    These are a distinct on/off type of event, analogous to pushing and
    releasing a button.  Just because they represent simple on or off state
    does not mean that the element's behavior isn't doing something complex
    while the trigger state is "on". For example think of a light that pulses
    while the state is "on", or a chase that repeats while its state is "on".
    Trigger events have an intensity value between 0-1, anything over 0 is an
    "on" trigger, while a trigger with value 0 is an "off" trigger.

Mapped Events
    These events change the value of some attribute of a element over time and
    might be connected to knobs, or sliders. For example you might have three
    knobs hooked up to an effect - one that controls the width of a pattern,
    one that controls the hue, and one that controls the cycle speed.

Birdfish takes events and renders them into channel output
----------------------------------------------------------

Birdfish takes a sequence of events, either pre-recorded or live/interactive,
and uses them to trigger and modify elements, which then, based on their
attributes and behaviors, will render channel data over time, which is sent
out to any connected lighting networks.

Lets work with an example.  A basic light element supports an attribute called
"attack".  The value of this attribute is the number of seconds it takes
a light to dim up from black to full intensity when it is triggered on - this
is also known as a fade-in.  In grid based software, this might be represented
as a ramp of increasing height from left to right. In Birdfish, it is simply
a property of the element.  A input's trigger event will cause the element to
start outputting first low values, and gradually brighter values over time
until full intensity is reached until an off trigger event is received.

Now a sequence of several minutes might have dozens of these trigger events. If
at a later time, you want to change the attack of a given light, you simply go
to where that element is defined, and give it a different attack value. No
changes need to be made to the sequence because the timing of the triggers is
all still correct. When the sequence plays again, Birdfish will once again
trigger the element, but now the element will render its channel output
differently, using the new attack value. This is just scratching the surface of
what this separation between event timing and channel output can yield.

Groups, Chases, and Effects
---------------------------

LightElement is the base object in an inheritance tree (class tree). RGBLight
is one that adds features for RGB, such as having a hue attribute that
automatically adjusts the R,G,and B channels to match a color of a certain Hue
in HSV colorspace (colorwheel).

In addition to subclasses for certain light types, there are also Groups
and Chases.  A group is simply a container object containing a set of
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


