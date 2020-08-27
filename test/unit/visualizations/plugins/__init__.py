import unittest

from galaxy.web.framework.base import WebApplication


class VisualizationsBase_TestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        WebApplication()
