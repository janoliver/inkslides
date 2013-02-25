#!/usr/bin/env python
# -=- encoding: utf-8 -=-

"""
This script generates a PDF presentation out of a single inkscape
document. In the inkscape document, there must be a layer named 
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

This script has the following dependencies:

  * inkscape
  * Python 3
  * python-lxml
  * PyPDF2      [Github](https://github.com/janoliver/PyPDF2)

The idea and many concepts of this script are taken from 
[inkscapeslide](https://github.com/abourget/inkscapeslide).

Copyright 2013, Jan Oliver Oelerich <janoliver@oelerich.org>
"""

import lxml.etree as xml
import copy
import subprocess
import PyPDF2
import tempfile
import argparse
import os

class InkscapeSlide(object):
    """
    This is the main class that does all the stuff. It is called
    as the following:

        >> i = InkscapeSlide()
        >> i.run("slides.svg")

    The class generates a "slides.pdf" in the same directory. 
    Depending on the number of slides, this may take a while.
    """

    # Input and output filenames
    f_input    = None  
    f_output   = None

    # the lxml root document 
    doc        = None

    # a list containing the description of all the slides and contents
    content    = None

    # temp folder to use
    tmp_folder = None

    # the XML namespaces we need.
    nsmap      = {
        'svg':      'http://www.w3.org/2000/svg',
        'inkscape': 'http://www.inkscape.org/namespaces/inkscape'
    }

    def run(self, file):
        """
        Carry out the parsing, creation of PDF files and so on.
        Main function. the only parameter is the input filename of the
        SVG slides.
        """

        self.f_input  = file
        self.f_output = "{}.pdf".format(os.path.splitext(file)[0])

        with tempfile.TemporaryDirectory() as self.tmp_folder:

            print("Parsing {} ...".format(self.f_input))
            self.parse()

            print("Creating SVG slides ...")
            svg_files = self.create_slides_svg()

            print("Creating PDF slides ...")
            pdf_files = self.create_slides_pdf(svg_files)

            print("Merging PDF slides ...")
            self.join_slides_pdf(pdf_files)

            print("Done creating {}".format(self.f_output))

    def parse(self):
        """
        Parse the input xml (svg) document and build up the 
        content description list.
        """
        parser = xml.XMLParser(ns_clean=True)
        self.doc = xml.parse(self.f_input, parser)

        self.content = self.get_content_description()
        self.hide_all(self.doc)

    def create_slides_svg(self):
        """
        This function creates inkscape svg files for each slide
        specified in the self.content list. Those are later converted
        to PDF by inkscape.
        """

        svg_files = list()

        for num, slide in enumerate(self.content):

            # we copy the document instance and work on that copy
            tmp_doc    = copy.deepcopy(self.doc)
            tmp_layers = self.get_layers(tmp_doc)

            # set the slide layers to visible and apply opacity
            for layer in slide:
                if len(layer) == 1: 
                    layer.append('1.0')

                self.show_layer(tmp_layers[layer[0]], layer[1])

            # select the hidden elements and delete them
            to_be_deleted = tmp_doc.xpath(
                  '/*/svg:g[@inkscape:groupmode="layer"][contains(\
                  @style, "display:none")]', 
                  namespaces=self.nsmap
            )
            
            for layer in to_be_deleted:
                layer.getparent().remove(layer)

            svg_path = '{1}/slide{0}.svg'.format(num, self.tmp_folder)
            tmp_doc.write(svg_path)
            svg_files.append(svg_path)

        return svg_files

    def create_slides_pdf(self, svg_files):
        """
        Generate PDF files out of the single svg files. These are
        later merged to the final presentation pdf. We re-use
        one inkscape process to speed up the generation.
        """

        # this is our inkscape worker
        ink = subprocess.Popen(['inkscape', '--shell'], 
                           stdin=subprocess.PIPE, 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.STDOUT)

        pdf_files = list()
        
        # main working loop of the inkscape process
        # we need to wait for ">" to see whether inkscape is ready.
        # The variable ready keeps track of that.
        ready = False
        while True:
            if ready:
                if not len(svg_files):
                    ink.kill()
                    break

                # take the first svg file and convert it to pdf
                svg_file = svg_files.pop(0)
                pdf_files.append("{}.pdf".format(svg_file))
                command = '-A {0}.pdf {0}\n'.format(
                    svg_file, self.tmp_folder
                )
                ink.stdin.write(bytes(command, 'utf-8'))

                ready = False
            else:
                if ink.stdout.read(1) == b'>':
                    ready = True

        return pdf_files
        
    def join_slides_pdf(self, pdf_files):
        """
        This function uses PyPDF2 to join the single PDF slides.
        """

        output = PyPDF2.PdfFileWriter()
        streams = list()
        for slide in pdf_files:
            stream = open(slide, "rb")
            pypdf_file = PyPDF2.PdfFileReader(stream)
            output.addPage(pypdf_file.getPage(0))
            streams.append(stream)
        
        with open(self.f_output, "wb") as out_file:
            output.write(out_file)
            for stream in streams: 
                stream.close

    def get_content_description(self):
        """
        Here, the "content" layer is parsed and the self.content
        array is being filled with the description of each slides 
        content.
        """

        content_lines = self.doc.xpath(
            '//svg:g[@inkscape:groupmode="layer"][\
            @inkscape:label="content"]/svg:text/svg:tspan[text()]', 
                  namespaces=self.nsmap
        )

        layers = list()
        for x in [l.text.strip() for l in content_lines]:
            cache = list()

            # if the line starts with a +, copy the last slide first
            if x.startswith('+'): 
                cache = layers[-1].copy()
                x = x[1:]

            # this is a bit cryptic. It decodes each slide and the 
            # corresponding opacity and writes in into the list.
            cache.extend([[d.strip() for d in c.split('*')] 
                    for c in x.split(',')])

            layers.append(cache)

        return layers

    def get_layers(self, doc):
        """
        Here, a dict of all the layers in the lxml svg document
        are built up. The key is a string, the layer's name, the 
        value is the lxml.Element object of the layer.
        """

        ret = dict()

        layers = doc.xpath(
            '//svg:g[@inkscape:groupmode="layer"]', 
            namespaces=self.nsmap
        )

        for layer in layers:
            ret[self.get_attr(layer, 'label')] = layer

        return ret

    def show_layer(self, layer, opacity=1.0):
        """
        Make a layer visible by setting the style= "display:inline"
        attribute.
        """

        styles = self.get_styles(layer)
        styles['display'] = 'inline'
        styles['opacity'] = str(opacity)
        self.set_styles(layer, styles)

    def hide_all(self, doc):
        """
        Hide all layers by setting the style= "display:none"
        attribute.
        """

        layers = self.get_layers(doc)
        for name, layer in layers.items():
            styles = self.get_styles(layer)
            styles['display'] = 'none'
            styles['opacity'] = '1.0'
            self.set_styles(layer, styles)

    def get_attr(self, el, attr, ns='inkscape'):
        """
        Get an attribute value of an lxml element "el"
        """

        return el.attrib.get(self.ns_join(attr,ns), False)

    def get_styles(self, el):
        """
        Get a dict of the content of the style="a:b;c:d" attribute
        """

        items = self.get_attr(el, 'style', 'svg')
        if not items: 
            return dict()
        return dict(item.split(':') for item in items.split(';'))

    def set_styles(self, el, styles):
        """
        Set the style="" attribute from a dict.
        """

        s = ";".join(["{}:{}".format(k,v) for k,v in styles.items()])
        el.attrib['style'] = s

    def ns_join(self, tag, namespace=None):
        """
        This function generates a {namespace}tag string out of a 
        namespace keyword and the tagname.
        """

        return '{%s}%s' % (self.nsmap[namespace], tag)

if __name__ == '__main__':
    # when the script is called directly...
     
    # command line args
    parser = argparse.ArgumentParser(description='Inkscapeslide.')
    parser.add_argument('file', metavar='svg-file', type=str,
                        help='The svg file to process')
    args = parser.parse_args()

    i = InkscapeSlide()
    i.run(file=args.file)
