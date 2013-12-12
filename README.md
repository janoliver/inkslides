# Inkscapeslide2

This script generates a PDF presentation out of a single inkscape
document. 

## Installation

Put the file `inkscapeslide.py` somewhere in your path (or into the 
directory your SVG presentation resides in and make it executable. 
(Although you can execute it by running `python inkscapeslide.py` as
well)

Alternatively, on Arch Linux, you can install the AUR package
[inkscapeslide2-git](https://aur.archlinux.org/packages/inkscapeslide2-git/).

## Dependencies

This script has the following dependencies:

  * inkscape
  * Python 3
  * python-lxml
  * PyPDF2      [Github](https://github.com/janoliver/PyPDF2)

## Usage

In the inkscape document, there must be a layer named 
"content" with a single text element. In that text element, each line
is one slide of the resulting presentation. The format is the following

    content layer text field
    ------------------------
    SlideA, SlideB
    SlideA*0.5, SlideB
    +SlideC

In this example, the first slide consists of the content of layers
SlideA and SlideB. The second slide would have the same content, 
except SlideA has an opacity of 0.5. The third layer is the second
but with SlideC also visible.

Then

    > chmod +x inkscapeslide.py
    > ./inkscapeslide.py presentation.svg

If you pass the parameter `-t, --temp`, then no temporary files are
kept by inkscapeslide. This, however, slows down the compilation,
because it recompiles all the slides!

## Acknowledgements

The idea and many concepts of this script are taken from 
[inkscapeslide](https://github.com/abourget/inkscapeslide).

