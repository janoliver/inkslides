#!/usr/bin/env python
# -=- encoding: utf-8 -=-

"""
# InkSlides

This script generates a PDF presentation out of a single inkscape
document.

## Installation

Put the file `inkslides.py` somewhere in your path (or into the
directory your SVG presentation resides in and make it executable.
(Although you can execute it by running `python inkscapeslide.py` as
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

    > chmod +x inkslides.py
    > ./inkslides.py presentation.svg

If you pass the parameter `-t, --temp`, then no temporary files are
kept by inkscapeslide. This, however, slows down the compilation,
because it recompiles all the slides!

In addition, you can give the `-w, --watch` parameter. If that one is
present, the script keeps running and watches the input SVG file for
changes. If one is detected, the presentation is automatically recompiled.

## Acknowledgements

The idea and many concepts of this script are taken from
[inkscapeslide](https://github.com/abourget/inkscapeslide).
"""

import lxml.etree as xml
import copy
import subprocess
import tempfile
import argparse
import os
import shutil
import hashlib
import sys
import time


__author__ = "Jan Oliver Oelerich"
__copyright__ = "Copyright 2013, Universitaet Marburg"
__credits__ = ["Jan Oliver Oelerich"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Jan Oliver Oelerich"
__email__ = "janoliver@oelerich.org"
__status__ = "Production"


class MergeFailedException(Exception):
    """Exception that indicates an Error during Merging of the PDF slides"""
    pass


class Merger(object):
    """
    Base class for a Merger. The type, python package or binary,
    should be indicated in the static type field. The function merge
    is handed a list of absolute paths to the single pdf slides,
    and is responsible for merging them in the correct order, so that
    the argument out_file is the merged PDF.
    """

    TYPE_BINARY = 1
    TYPE_PACKAGE = 2

    type = TYPE_BINARY

    def merge(self, slides, out_file):
        """Merges the slides and writes the result to out_file"""

        raise NotImplementedError


class PyPDFMerger(Merger):
    """
    Uses the PyPDF2 package to merge the PDFs.
    """

    type = Merger.TYPE_PACKAGE

    def merge(self, slides, out_file):

        try:
            import PyPDF2

            output = PyPDF2.PdfFileWriter()
            streams = list()
            for slide in slides:
                stream = open(slide, "rb")
                pypdf_file = PyPDF2.PdfFileReader(stream)
                output.addPage(pypdf_file.getPage(0))
                streams.append(stream)

            with open(out_file, "wb") as out_stream:
                output.write(out_stream)
                for stream in streams:
                    stream.close()

        except:
            raise MergeFailedException("Could not merge using PyPDF2")


class TexliveMerger(Merger):
    """
    Uses the ghostscript binary `gs` to merge the slides. ghostscript
    is usually included in Texlive installations and is probably available
    on most Linux machines.
    """

    def merge(self, slides, out_file):
        command = ["gs", "-dBATCH", "-dNOPAUSE", "-q", "-sDEVICE=pdfwrite",
                   "-dPDFSETTINGS=/prepress",
                   "-sOutputFile=%s" % out_file]

        for slide in slides:
            command.append(slide)

        if subprocess.call(command):
            raise MergeFailedException("Could not merge using %s" % command)


class PopplerMerger(Merger):
    """
    Uses the binary `pdfunite` to merge the PDF files, which is included in
    the Poppler PDF engine, which is probably available on your machine.
    """

    def merge(self, slides, out_file):
        command = ["pdfunite"]

        for slide in slides:
            command.append(slide)

        command.append(out_file)

        if subprocess.call(command):
            raise MergeFailedException("Could not merge using %s" % command)


class MergerWrapper(object):
    """
    This class looks for available tools to merge PDF files and, if a suitable
    one is found, provides the merge() function to execute the merge.
    """

    TOOLS = (
        ('PyPDF2', PyPDFMerger),
        ('pdfunite', PopplerMerger),
        ('gs', TexliveMerger),
    )

    def __init__(self):
        self.merger = self.find_merging_tool()()

        if not self.merger:
            raise MergeFailedException("No tool to merge PDF Files available")

    def merge(self, slides, tmp_dir):
        self.merger.merge(slides, tmp_dir)

    def find_merging_tool(self):
        """Tests, which of the merger tools is available on the computer."""

        for command, merger in self.TOOLS:

            if merger.type == Merger.TYPE_BINARY:
                if self.which(command):
                    return merger

            elif merger.type == Merger.TYPE_PACKAGE:
                try:
                    __import__(command)
                    return merger

                except ImportError:
                    continue

        return None

    @staticmethod
    def which(program):
        """Resembles Unix's `which` utility, to check for executables.
        Stolen from Stackoverflow. :)"""

        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        fpath, fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file

        return None


class InkSlides(object):
    """
    This is the main class that does all the stuff. It is called
    as the following:

        >> i = InkSlides()
        >> i.run("slides.svg")

    The class generates a "slides.pdf" in the same directory. 
    Depending on the number of slides, this may take a while.
    """
    nsmap = {
        'svg': 'http://www.w3.org/2000/svg',
        'inkscape': 'http://www.inkscape.org/namespaces/inkscape',
        'sodipodi': 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'
    }

    def __init__(self):

        # Input and output filenames
        self.f_input = None
        self.f_output = None

        # the lxml root document and some containers
        self.doc = None
        self.svg_files = None
        self.pdf_files = None

        # a list containing the description of all the slides and contents
        self.content = None

        # temp folder to use
        self.tmp_folder = None

    def runwatch(self, file, temp=True):

        print("Started continuous mode! Cancel with Ctrl+C")

        state = None

        while 1:
            mtime = os.stat(file).st_mtime

            if mtime != state:
                print("Change detected. Recompiling...")
                self.run(file, temp)
                state = mtime

            time.sleep(.5)

    def run(self, file, temp=True):
        """
        Carry out the parsing, creation of PDF files and so on.
        Main function. the only parameter is the input filename of the
        SVG slides.
        """

        self.f_input = file
        self.f_output = "{}.pdf".format(os.path.splitext(file)[0])

        self.setup_temp_folder(temp)

        print("Parsing {} ...".format(self.f_input))
        self.parse()

        print("Creating SVG slides ...")
        if self.create_slides_svg():
            print("PDF should be up to date. Quitting ...")
            return

        print("Creating PDF slides ...")
        self.create_slides_pdf()

        print("Merging PDF slides ...")
        self.join_slides_pdf()

        # remove the temp folder, if the keep option was not set
        self.clear_temp_folder(temp)

        print("Done creating {}.".format(self.f_output))

    def setup_temp_folder(self, temp):
        # create (or detect) the temporary directory. If the keep option was
        # set, we use ./.inkslides as temp folder. if it exists, we reuse
        # stuff from there. this speeds up everything by a lot. Otherwise,
        # create a temp folder in /tmp
        if not temp:
            base = os.path.splitext(os.path.basename(self.f_input))[0]
            self.tmp_folder = './.inkslides-%s' % base
            if not os.path.exists(self.tmp_folder):
                os.makedirs(self.tmp_folder)
        else:
            self.tmp_folder = tempfile.mkdtemp()

    def clear_temp_folder(self, temp):
        if temp:
            shutil.rmtree(self.tmp_folder)

    def parse(self):
        """
        Parse the input xml (svg) document and build up the 
        content description list.
        """
        parser = xml.XMLParser(ns_clean=True, huge_tree=True)
        self.doc = xml.parse(self.f_input, parser)

        # find the content descriptor, i.e., which slides to include when + how
        self.content = self.get_content_description()

        # set all elements in the pdf to hidden
        self.hide_all(self.doc)

    def create_slides_svg(self):
        """
        This function creates inkscape svg files for each slide
        specified in the self.content list. Those are later converted
        to PDF by inkscape.
        """

        only_cached = True
        self.svg_files = list()

        for num, slide in enumerate(self.content):

            svg_path = '{1}/slide-{0}.svg'.format(num, self.tmp_folder)

            # we copy the document instance and work on that copy
            tmp_doc = copy.deepcopy(self.doc)
            tmp_layers = self.get_layers(tmp_doc)

            # set the slide layers to visible and apply opacity
            for layer in slide:
                if len(layer) == 1:
                    layer.append('1.0')

                self.show_layer(tmp_layers[layer[0]], layer[1])

            # add the hidden elements to the to-delete list
            to_be_deleted = tmp_doc.xpath(
                '/*/svg:g[@inkscape:groupmode="layer"][contains(\
                @style, "display:none")]',
                namespaces=self.nsmap
            )

            # add the sodipodi:namedview element, which is just inkscape
            # related stuff
            to_be_deleted.append(
                tmp_doc.xpath('//sodipodi:namedview', namespaces=self.nsmap
                )[0])

            # delete them
            for layer in to_be_deleted:
                layer.getparent().remove(layer)

            # calculate the sha256 hash of the current svg file, write svg
            # to file
            # and recalculate the hash
            cached = os.path.exists(svg_path)
            if cached:
                old_hash = hashlib.sha256(open(svg_path, 'rb').read()).digest()

            tmp_doc.write(svg_path)

            if cached:
                new_hash = hashlib.sha256(open(svg_path, 'rb').read()).digest()

                # if the hashes are equal AND the corresponding pdf file exists,
                # we can use the cached version and don't have to go through
                # inkscape again. yay!
                cached = old_hash == new_hash and os.path.exists(
                    self.pdf_from_svg(svg_path))

            self.svg_files.append((svg_path, cached))

            if not cached:
                only_cached = False

        return only_cached

    def create_slides_pdf(self):
        """
        Generate PDF files out of the single svg files. These are
        later merged to the final presentation pdf. We re-use
        one inkscape process to speed up the generation.
        """

        if sys.version < '3':
            def c_bytes(string, enc):
                return bytes(string)
        else:
            def c_bytes(string, enc):
                return bytes(string, enc)

        # this is our inkscape worker
        ink = subprocess.Popen(['inkscape', '--shell'],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)

        self.pdf_files = list()

        # main working loop of the inkscape process
        # we need to wait for ">" to see whether inkscape is ready.
        # The variable ready keeps track of that.
        ready = False
        counter = 0
        num_all = len(self.svg_files)
        while True:
            if ready:
                if not len(self.svg_files):
                    ink.kill()
                    break

                svg_file, cached = self.svg_files.pop(0)
                pdf_file = self.pdf_from_svg(svg_file)

                # calculate percent of advance
                counter += 1
                percent = int(round(100. * counter / num_all))

                self.pdf_files.append(pdf_file)

                # if no cached version, create new pdf by inkscape
                # else skip this slide
                if not cached:
                    command = '-A "{1}" "{0}"\n'.format(svg_file, pdf_file)
                    ink.stdin.write(command.encode("UTF-8"))
                    ink.stdin.flush()

                    print("  Converted {0} ({1:d}%)".format(
                        pdf_file, percent
                    ))

                    ready = False

                else:
                    print("  Skipping {0} ({1:d}%)".format(
                        pdf_file, percent
                    ))

            else:
                if ink.stdout.read(1) == b'>':
                    ready = True

    def join_slides_pdf(self):
        """
        This function uses PyPDF2 to join the single PDF slides.
        """

        merger = MergerWrapper()
        merger.merge(self.pdf_files, self.f_output)

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
                cache = copy.copy(layers[-1])
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

        return el.attrib.get(self.ns_join(attr, ns), False)

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

        s = ";".join(sorted(["{}:{}".format(k, v) for k, v in styles.items()]))
        el.attrib['style'] = s

    def ns_join(self, tag, namespace=None):
        """
        This function generates a {namespace}tag string out of a 
        namespace keyword and the tagname.
        """

        return '{%s}%s' % (self.nsmap[namespace], tag)

    def pdf_from_svg(self, svg_file_name):
        return ".".join(svg_file_name.split('.')[:-1]) + '.pdf'


if __name__ == '__main__':
    # when the script is called directly...

    # command line args
    parser = argparse.ArgumentParser(description='Inkscapeslide.')
    parser.add_argument('-t', '--temp', action='store_true',
        help='don\'t keep the temporary files to speed up compilation')
    parser.add_argument('-w', '--watch', action='store_true',
        help='watch the input file for changes and automatically recompile')
    parser.add_argument('file', metavar='svg-file', type=str,
        help='The svg file to process')
    args = parser.parse_args()

    i = InkSlides()

    if args.watch:
        i.runwatch(file=args.file, temp=args.temp)
    else:
        i.run(file=args.file, temp=args.temp)
