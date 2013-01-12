Structuring the show file
=========================

The show file is the main script that will put together all the pieces that are
specific to your setup. It is where you define what lights, networks,
controllers and inputs you have and virtually wire them all up.

Create the show object

birdfish.lights.LightShow is the item that orchestrates the timing of the show.
It contains a runloop that calls an update function multiple times a second
depending on your framerate. 
defining networks

defining elements

Connecting elements to networks

defining inputs

connecting inputs to elements

The flow of how it works
