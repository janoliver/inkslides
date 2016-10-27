# InkSlides

This script generates a PDF presentation out of a single inkscape
document. You create your slides as layers in an SVG file and `inkslides`
generates a PDF presentation for you. 

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

## SVG structure

inkslides decides, what to include in the presentation, by looking at the 
layer structure of the SVG file. A layer is included if it is a sublayer of 
any other layer. When it contains another level of layers, i.e., sublayers 
of sublayers, these are included one by one while their siblings are still 
visible. For example, consider this layer structure:

```
Polar bears
  Why polar bears are cool
    Argument 3
    Argument 2
    Argument 1
  Weaknesses of polar bears
Title
  Welcome
```

This would result in a PDF with the following slides, where each line 
contains the visible layers on one page.

```
Title,Welcome
Polar beares,Why polar bears are cool,Argument 1
Polar beares,Why polar bears are cool,Argument 1,Argument 2
Polar beares,Why polar bears are cool,Argument 1,Argument 2,Argument 3
Polar beares,Weaknesses of polar bears
```

As you can see, the polar bear slide builds up its argument as frames, much 
like it is known from usual PowerPoint presentations. If there are no 
sublayers of sublayers, we end up with a simple slide without any frames.

To reuse common layers you can, at any layer that is not a root layer, 
import other layers by defining a text element whose first line contains 
`#import#`. The following lines should contain the name of the layers to 
be imported. For example

```
#import#
Argument 3
Weaknesses of polar bears
```

would import the two named layers into the current one. Note: If any of 
the layers to be imported has a `-` (minus) sign prefixed, it will not 
be imported but rather _deleted_ from the current layer list. This is 
particularly useful for the master layer function explained hereafter.

Lastly, inkslides searches for a text element starting with `#master#`. 
The syntax is similar to the `#import#` structure. All layers you list in 
the master block are visible on every single slide of your presentation. 
You may disable them by an `#import#` directive with one of the master 
layers prefixed with a `-`. Note, that the master block can appear 
_anywhere_ in your SVG file. 

If multiple `#master#` blocks are found globally, or multiple `#import#` 
blocks are present in one layer, the first one is chosen and the others 
are ignored. 

## script usage
```
> chmod +x inkslides.py
> ./inkslides.py example.svg
```

If you pass the parameter `-t, --temp`, then no temporary files are
kept by inkscapeslide. This, however, slows down the compilation,
because it recompiles all the slides!

In addition, you can give the `-w, --watch` parameter. If that one is 
present, the script keeps running and watches the input SVG file for 
changes. If one is detected, the presentation is automatically recompiled.

Try not to embed images but link them, otherwise the file will be huge.

To compress the output PDF files, you may use ghostcript. For example:

```
> gs -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -dDownsampleColorImages=true -dColorImageResolution=150 -dCompatibilityLevel=1.4 -sOutputFile=$output$.pdf $input$.pdf
```

## Acknowledgements

The idea and many concepts of this script are taken from 
[inkscapeslide](https://github.com/abourget/inkscapeslide).

## Modified

Johannes Graeter: added slide enumeration
Johannes Graeter: added structuring by layers
