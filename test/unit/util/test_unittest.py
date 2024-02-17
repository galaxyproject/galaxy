from galaxy.util.unittest import TestCase


class TestTestCase(TestCase):
    j: str

    @classmethod
    def setUpClass(cls):
        cls.j = "foo"

    def setUp(self):
        self.i = 1

    def test_setUpClass(self):
        assert self.j == "foo"

    def test_setUp(self):
        assert self.i == 1

    def test_assertRaises(self):
        with self.assertRaises(ZeroDivisionError):
            1 / 0  # noqa: B018

    def test_assertRaisesRegex(self):
        with self.assertRaisesRegex(ZeroDivisionError, "^division .* zero"):
            1 / 0  # noqa: B018
