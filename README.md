# InkSlides

`inkslides` generates a PDF presentation out of an inkscape SVG
document. The order of slides and visibility of content is determined
by the layer structure of the SVG. 

## Installation

Clone the repository somewhere and type

```
> python setup.py install
```

## Requirements

This program has the following requirements:

  * Linux (currently)
  * inkscape
  * Python >= 2.7
  * python-lxml (or python2-lxml)
  * Any one of: PyPDF2, ghostscript (comes with TeXLive), pdfunite

## Usage

### SVG layer structure

`inkslides` decides, what to include in the presentation, by looking at the 
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

This would result in a PDF with the following slides, where each line contains 
the visible layers on one page.

```
Title,Welcome
Polar bears,Weaknesses of polar bears
Polar bears,Why polar bears are cool,Argument 1
Polar bears,Why polar bears are cool,Argument 1,Argument 2
Polar bears,Why polar bears are cool,Argument 1,Argument 2,Argument 3
```

As you can see, the layers in the third level of the layer tree are treated as 
frames, where the previous slides stay visible. If there are no sublayers of 
sublayers, we end up with a simple slide without any frames.

### Text directives

#### import layers 

To reuse common layers you can, in any layer (except `root`), import 
other layers by defining a text element whose first line starts with `#import#`. 
The subsequent lines should contain the name of layers to be imported. For 
example:

```
#import#
Argument 3
Weaknesses of polar bears
```

would make the two layers `Argument 3` and `Weaknesses of polar bears` visible,
regardless of where in the presentation we are right now. 

If any of the layers in an `#import#` block is prefixed with a `-` (minus) sign, 
it won't be imported but rather _deleted_ from the current layer list. This is 
particularly useful for the `#master'` block (see below).

#### master layers

`inkslides` searches for a text element starting with `#master#`. The syntax is 
similar to the `#import#` structure. All layers you list in the master block are 
visible on every single slide of your presentation. You may disable them by an 
`#import#` directive with one of the master layers prefixed with a `-`. Note, 
that the master block can appear _anywhere_ in your SVG file. 

If multiple `#master#` blocks are found globally, or multiple `#import#` blocks 
are present in one layer, the first one is chosen and the others are ignored. 

### compile the presentation

```
> inkslides example.svg
```

If you pass the parameter `-t, --temp`, then no temporary files are
kept by `inkslides`. This slows down the compilation but may help during 
development or debugging.

In addition, you can give the `-w, --watch` parameter. If it is 
present, the program keeps running and watches the input SVG file for 
changes. If changes are detected, the presentation is automatically recompiled.

Try not to embed images but link them to reduce file sizes.

To compress the output PDF files, you may use ghostcript. For example:

```
> gs -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -dDownsampleColorImages=true -dColorImageResolution=150 -dCompatibilityLevel=1.4 -sOutputFile=$output $input

```

## Acknowledgements

The idea and many concepts of this script are taken from 
[inkscapeslide](https://github.com/abourget/inkscapeslide).

## Modified

  * Johannes Graeter: added slide enumeration
  * Johannes Graeter: added structuring by layers
