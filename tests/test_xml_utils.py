# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import unittest
import os

from clairmeta.utils.xml import parse_xml
from clairmeta.utils.sys import remove_key_dict


class ParseTest(unittest.TestCase):

    def get_file_path(self, name):
        file_path = os.path.join(
            os.path.dirname(__file__),
            'resources', 'XML', name)

        self.assertTrue(os.path.exists(file_path))
        return file_path

    def test_attributes(self):
        xml_with_attrib = parse_xml(self.get_file_path('CPL_SMPTE.xml'))
        xml_without_attrib = parse_xml(
            self.get_file_path('CPL_SMPTE.xml'), xml_attribs=False)
        self.assertNotEqual(xml_with_attrib, xml_without_attrib)

        xml_with_attrib = remove_key_dict(xml_with_attrib, ['@'])
        self.assertEqual(xml_with_attrib, xml_without_attrib)


if __name__ == '__main__':
    unittest.main()
