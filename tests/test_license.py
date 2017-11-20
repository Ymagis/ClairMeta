# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import unittest
import os


template_lines = [
    "# Clairmeta - (C) YMAGIS S.A.\n",
    "# See LICENSE for more information\n"]

source_folder = os.path.dirname(os.path.dirname(__file__))
source_folder = os.path.join(source_folder, 'sources')


class LicenseTest(unittest.TestCase):

    def file_contain_license(self, path):
        with open(path, 'r') as fhandle:
            lines = fhandle.readlines()
            lines = [l for l in lines if l != "" and not l.startswith('#!')]
            return all([a == b for a, b in zip(template_lines, lines)])

    def test_sources_have_license(self):
        for dirpath, dirnames, filenames in os.walk(source_folder):
            for f in filenames:
                if f.endswith('.py'):
                    fpath = os.path.join(dirpath, f)
                    self.assertTrue(
                        self.file_contain_license(fpath),
                        msg="Missing license for file {}".format(f))


if __name__ == '__main__':
    unittest.main()
