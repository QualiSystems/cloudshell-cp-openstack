import unittest

from cloudshell.template.package import info


class TestPackage(unittest.TestCase):
    def test_package(self):
        self.assertEqual("info", info)
