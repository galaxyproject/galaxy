import pytest


class TestCase:
    """Partial re-implementation of standard library unittest.TestCase using
    pytest methods
    See https://docs.pytest.org/en/latest/how-to/xunit_setup.html for a
    description of the pytest setup/teardown methods.

    Most assert*() methods of unittest.TestCase are not reimplemented here on
    purpose, normal assert statements should be used instead."""

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def setup_class(cls):
        cls.setUpClass()

    @classmethod
    def tearDownClass(cls):
        pass

    @classmethod
    def teardown_class(cls):
        cls.tearDownClass()

    def setUp(self):
        pass

    def setup_method(self):
        self.setUp()

    def tearDown(self):
        pass

    def teardown_method(self):
        self.tearDown()

    def assertRaises(self, exception):
        return pytest.raises(exception)

    def assertRaisesRegex(self, exception, regex):
        return pytest.raises(exception, match=regex)
