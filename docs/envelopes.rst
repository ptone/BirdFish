=========
Envelopes
=========

Envelopes are tool used in Birdfish when designing effects. They
allow you to describe how something changes over time or distance in a flexible
and powerful way.

Introduction
------------

Envelopes are used in many ways, and can be confusing in their abstraction, so
lets start with a super simple example: a fade in.

We can describe a fade in as starting at zero, going to one, and taking
one second.

.. Note:: 
    Most values in Birdfish are floating point numbers between 0-1 instead of
    0-255 as in DMX, channel values are converted to 0-255 for network output.

In a conventional grid based approach - where a second might be divided into
ten slices, this might look something like this:

.. image:: /images/grid-fadein.png

Whereas if time is divided into an infinite number of slices - this fade in
would simply be represented as a line, a simple linear slope.

.. image:: /images/linear-slope.png

This line can be encapsulated as an envelope - and can be applied to attributes
of elements, such as intensity, or hue. It can also be applied to the position
of a chase, being a start and end position over time.

A linear change may be the most familiar, but far more dynamic results can be
achieved with curves that travel from point A to point B in some non-linear
way. These types of curves are often used in animations, and are sometimes
referred to as easing curves or tweens and can be illustrated like this:

.. image:: /images/curves.png

Many times, the behavior you are looking for can't be described by just one
function. In these cases, curves are joined together in an evenlope, where each
curve is a segment. For example, here is a more complex envelope consisting of
four segments.

.. image:: /images/envelope-segments.png


ADSR
----

The concept of envelopes is used frequently in music synthesizers. One classic
envelope is the Attack-Decay-Sustain-Release, or ADSR, envelope. In
synthesizers this describes how the volume of the sound changes over time, but
we can apply this concept to light intensity (the color reference the segmented
envelope figure above).

* Attack (red) - is the fade in.
* Decay (green) - is a fade to the held level.
* Sustain (blue) - is the level at which the intensity is held as long as the trigger
  is on.
* Release (yellow) is the fade out, which begins when the off trigger happens

This 4 part envelope is built into light elements directly, and can be modified
simply be changing their attack, decay, sustain, or release attributes.
