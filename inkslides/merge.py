import os
import subprocess


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
