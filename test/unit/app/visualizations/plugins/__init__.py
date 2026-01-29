import routes

from galaxy.util.unittest import TestCase


class VisualizationsBase_TestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        routes.Mapper()
