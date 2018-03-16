#!/usr/bin/env python
# -=- encoding: utf-8 -=-

"""
# InkSlides

This script generates a PDF presentation out of a single inkscape
document.
"""

import argparse
import copy
import hashlib
import multiprocessing
import os
import shutil
import subprocess
import sys
import tempfile
import time
from multiprocessing import Queue

from lxml.etree import XMLParser, parse

from .inkscape import InkscapeWorker
from .merge import MergerWrapper
from .utils import *

__author__ = "Jan Oliver Oelerich"
__copyright__ = "Copyright 2013, Universitaet Marburg"
__credits__ = ["Jan Oliver Oelerich"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Jan Oliver Oelerich"
__email__ = "janoliver@oelerich.org"
__status__ = "Production"


class InkSlides(object):
    """
    This is the main class that does all the stuff. It is called
    as the following:

        >> i = InkSlides()
        >> i.run("slides.svg")

    The class generates a "slides.pdf" in the same directory. 
    Depending on the number of slides, this may take a while.
    """

    def __init__(self, num_workers, flat=False):

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

        self.num_workers = num_workers

        self.flat = flat

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

        print("Creating PDF slides in parallel on {} workers...".format(self.num_workers))

        # spawn a pool of workers and set up a request queue
        # see http://stackoverflow.com/a/9039979/169748
        workers = []
        request_queue = Queue()
        for i in range(self.num_workers):
            workers.append(InkscapeWorker(request_queue))

        # start workers
        for w in workers:
            w.start()

        # populate the queue
        self.pdf_files = []
        for svg_file, cached in self.svg_files:
            pdf_file = self.pdf_from_svg(svg_file)
            self.pdf_files.append(pdf_file)
            request_queue.put((svg_file, pdf_file, cached))

        # Sentinel objects to allow clean shutdown: 1 per worker.
        for i in range(self.num_workers):
            request_queue.put(None)

        # wait for workers to be finished
        for w in workers:
            w.join()

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
        parser = XMLParser(ns_clean=True, huge_tree=True)
        self.doc = parse(self.f_input, parser=parser)

        # find the content descriptor, i.e., which slides to include when + how
        # self.content = self.get_content_description()
        self.content = self.get_layer_structure() if not self.flat else self.get_flat_layer_structure()

        # set all elements in the pdf to hidden
        hide_all_layers(self.doc)

    def create_slides_svg(self):
        """
        This function creates inkscape svg files for each slide
        specified in the self.content list. Those are later converted
        to PDF by inkscape.
        """

        only_cached = True
        self.svg_files = list()

        for frame_num, (slide_num, slide) in enumerate(self.content):

            svg_path = '{1}/slide-{0}.svg'.format(frame_num, self.tmp_folder)

            # we copy the document instance and work on that copy
            tmp_doc = copy.deepcopy(self.doc)
            tmp_layers = get_all_layers(tmp_doc)

            # set the slide layers to visible and apply opacity 1.0
            do_delete = True
            for layer in slide:
                show_layer(tmp_layers[layer])
                if tmp_layers[layer].xpath('.//svg:use', namespaces=nsmap):
                    do_delete = False

            if do_delete:
                # add the hidden elements to the to-delete list
                to_be_deleted = tmp_doc.xpath(
                    '/*/svg:g[@inkscape:groupmode="layer"][contains(\
                    @style, "display:none")]',
                    namespaces=nsmap
                )

                # add the sodipodi:namedview element, which is just inkscape
                # related stuff
                to_be_deleted.append(
                    tmp_doc.xpath('//sodipodi:namedview', namespaces=nsmap)[0])

                # delete them
                for layer in to_be_deleted:
                    layer.getparent().remove(layer)

            # calculate the sha256 hash of the current svg file, write svg
            # to file
            # and recalculate the hash
            cached = os.path.exists(svg_path)
            if cached:
                old_hash = hashlib.sha256(open(svg_path, 'rb').read()).digest()

            # replace text elements containing #num# with the slide number
            for e in tmp_doc.xpath('//svg:text/svg:tspan[text()="#num#"]', namespaces=nsmap):
                e.text = str(slide_num)

            # replace text elements containing #num# with the slide number
            for e in tmp_doc.xpath('//svg:text/svg:tspan[text()="#frame_num#"]', namespaces=nsmap):
                e.text = str(frame_num)

            tmp_doc.write(svg_path)

            if cached:
                new_hash = hashlib.sha256(open(svg_path, 'rb').read()).digest()

                # if the hashes are equal AND the corresponding pdf file exists,
                # we can use the cached version and don't have to go through
                # inkscape again. yay!
                cached = old_hash == new_hash and os.path.exists(self.pdf_from_svg(svg_path))

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

    def add_master_layers(self, current_layers):
        # this function checks for a #master# text element anywhere and, if present, adds the
        # following lines as layers to current_layers
        cur_content_lines = self.doc.xpath('//svg:text/svg:tspan[starts-with(text(),"#master#")]/..', namespaces=nsmap)

        if cur_content_lines and len(cur_content_lines[0]) > 0:
            for l in cur_content_lines[0][1:]:
                if l.text is not None:
                    current_layers.append(l.text.strip())

    def add_imported_layers(self, layer, current_layers):
        # this function checks for a #content# text element and, if present, adds the
        # following lines as layers to current_layers
        cur_content_lines = layer.xpath('./svg:text/svg:tspan[starts-with(text(),"#import#")]/..', namespaces=nsmap)

        if cur_content_lines and len(cur_content_lines[0]) > 0:
            for l in cur_content_lines[0][1:]:
                if l.text is not None:
                    if l.text[0] == "-":
                        current_layers.remove(l.text[1:])
                    else:
                        current_layers.append(l.text.strip())

    def get_layer_structure(self):
        """
        Determine the layer structure
        """
        slide_tree = []
        num_slide = 0

        # iterate in reverse because svg is formated in this way
        for sec in self.doc.getroot().xpath('./svg:g[@inkscape:groupmode="layer"]', namespaces=nsmap):

            for slide in sec.xpath('./svg:g[@inkscape:groupmode="layer"]', namespaces=nsmap):

                num_slide += 1

                current_slide = [get_label(sec), get_label(slide)]
                self.add_master_layers(current_slide)
                self.add_imported_layers(slide, current_slide)

                sublayers = slide.xpath('./svg:g[@inkscape:groupmode="layer"]', namespaces=nsmap)

                if sublayers:
                    # here, the sublayers of the sublayer are present, which are treated as frames.
                    # We add them as frames to slide_tree

                    for sublayer in sublayers:
                        current_slide.append(get_label(sublayer))
                        self.add_imported_layers(sublayer, current_slide)
                        slide_tree.append((num_slide, current_slide[:]))

                else:
                    # no sublayers present, we therefore add the current layer
                    slide_tree.append((num_slide, current_slide[:]))

        return slide_tree

    def get_flat_layer_structure(self):
        """
        Determine the layer structure
        """
        slide_tree = []
        num_slide = 0

        # iterate in reverse because svg is formated in this way
        for slide in self.doc.getroot().xpath('./svg:g[@inkscape:groupmode="layer"]', namespaces=nsmap):
            num_slide += 1
            current_slide = [get_label(slide)]
            self.add_master_layers(current_slide)
            self.add_imported_layers(slide, current_slide)
            slide_tree.append((num_slide, current_slide[:]))

        return slide_tree

    def pdf_from_svg(self, svg_file_name):
        return ".".join(svg_file_name.split('.')[:-1]) + '.pdf'


def main():
    # when the script is called directly...

    # command line args
    parser = argparse.ArgumentParser(description='Inkscapeslide.')
    parser.add_argument('-t', '--temp', action='store_true',
                        help='don\'t keep the temporary files to speed up compilation')
    parser.add_argument('-w', '--watch', action='store_true',
                        help='watch the input file for changes and automatically recompile')
    parser.add_argument('--flat', action='store_true',
                        help='Ignore sublayers and simply let each top level layer be one slide.')
    parser.add_argument('-p', '--parallel-workers', type=int, default=multiprocessing.cpu_count(),
                        help='The number of inkscape workers to spawn.')
    parser.add_argument('file', metavar='svg-file', type=str, help='The svg file to process')
    args = parser.parse_args()

    i = InkSlides(args.parallel_workers, flat=args.flat)

    if args.watch:
        i.runwatch(file=args.file, temp=args.temp)
    else:
        i.run(file=args.file, temp=args.temp)
