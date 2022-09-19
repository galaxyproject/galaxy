import unittest

import routes


class VisualizationsBase_TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        routes.Mapper()
