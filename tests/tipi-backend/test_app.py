import unittest

class TestApp(unittest.TestCase):

    def inc(self, x):
        return x + 1

    def test_answer(self):
        assert self.inc(3) == 4

if __name__ == '__main__':
    unittest.main()
