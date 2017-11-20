# Clairmeta - (C) YMAGIS S.A.
# See LICENSE for more information

import unittest
import os

from clairmeta.profile import load_profile


GOOD_PROFILE = os.path.join(os.path.dirname(__file__), 'resources/myprofile.json')


class ProfileTest(unittest.TestCase):

    def test_load_profile(self):
        p = load_profile(GOOD_PROFILE)
        self.assertEqual(p['log_level'], 'INFO')
        self.assertEqual(p['bypass'], ["check_assets_pkl_hash"])
        self.assertEqual(p['criticality']['default'], 'ERROR')


if __name__ == '__main__':
    unittest.main()
