# Inkscapeslide2 ![](https://stats.oelerich.org/piwik.php?idsite=12&amp;rec=1)

This script generates a PDF presentation out of a single inkscape
document. 

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

## Dependencies

This script has the following dependencies:

  * inkscape
  * Python 3
  * python-lxml
  * PyPDF2      [Github](https://github.com/janoliver/PyPDF2)

## Acknowledgements

The idea and many concepts of this script are taken from 
[inkscapeslide](https://github.com/abourget/inkscapeslide).

## Copyright

Copyright 2013, Jan Oliver Oelerich <janoliver@oelerich.org>
