# InkSlides

This script generates a PDF presentation out of a single inkscape
document. 

## Installation

Put the file `inkslides.py` somewhere in your path (or into the
directory your SVG presentation resides in and make it executable. 
(Although you can execute it by running `python inkslides.py` as
well)

Alternatively, on Arch Linux, you can install the AUR package
[inkslides-git](https://aur.archlinux.org/packages/inkslides-git/).

## Dependencies

This script has the following dependencies:

  * Linux (currently)
  * inkscape
  * Python >= 2.7
  * python-lxml (or python2-lxml)
  * Any one of: PyPDF2, ghostscript (comes with TeXLive), pdfunite

## Usage

The inkscape document must be structured as the file example.svg in this folder:

Each slide consists of a layer of sublayers.
On each sublayer you can define the part of the slide that should be overlain over the precedent layers.
In that way you can realize animations while structuring your presentation.
You may structure your svg files by putting the "slide" layers into groups.
Slides and groups can therefore be deactivated by only one click on the "eye" icon in the layer menu.

To reuse common layers you can specify links to layers by including a text-field with 
"#content#
Sublayer1, Sublayer2"

No seperate structuring layer is needed anymore.

Then

    > chmod +x inkslides.py
    > ./inkslides.py example.svg

If you pass the parameter `-t, --temp`, then no temporary files are
kept by inkscapeslide. This, however, slows down the compilation,
because it recompiles all the slides!

In addition, you can give the `-w, --watch` parameter. If that one is 
present, the script keeps running and watches the input SVG file for 
changes. If one is detected, the presentation is automatically recompiled.

Johannes Graeter:
-Don't embed images but link them otherwise the file will be huge.

-To compress the output pdf-files use ghostcript, f.e.
 gs -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -dDownsampleColorImages=true -dColorImageResolution=150 -dCompatibilityLevel=1.4 -sOutputFile=$output$.pdf $input$.pdf

## Acknowledgements

The idea and many concepts of this script are taken from 
[inkscapeslide](https://github.com/abourget/inkscapeslide).

##Modified
Johannes Graeter: added slide enumeration
Johannes Graeter: added structuring by layers

## TODO 
Video embedding

