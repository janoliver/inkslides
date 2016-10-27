import multiprocessing
import subprocess


class InkscapeWorker(multiprocessing.Process):
    def __init__(self, queue):
        super(InkscapeWorker, self).__init__()
        self.queue = queue

    def wait_for_inkscape(self):
        while self.ink.stdout.read(1) != b'>':
            pass

    def run(self):
        # this is our inkscape worker
        self.ink = subprocess.Popen(['inkscape', '--shell'],
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)

        # first, wait for inkscape startup
        self.wait_for_inkscape()

        for svg_file, pdf_file_name, cached in iter(self.queue.get, None):

            # main working loop of the inkscape process
            # we need to wait for ">" to see whether inkscape is ready.
            # The variable ready keeps track of that.

            if not cached:
                command = '-A "{1}" "{0}"\n'.format(svg_file, pdf_file_name)
                self.ink.stdin.write(command.encode("UTF-8"))
                self.ink.stdin.flush()

                self.wait_for_inkscape()

                print("  Converted {0}".format(pdf_file_name))
            else:
                print("  Skipping {0}".format(pdf_file_name))

