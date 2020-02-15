import unittest
import sys
sys.path.append('/app')

from tipi_backend.app import create_app
from tipi_backend.settings import Config


class TestLimit(unittest.TestCase):

    def setUp(self):
        Config.TESTING = True
        app = create_app(config=Config)
        self.client = app.test_client()


    def test_limit_label_extract(self):
        data = {'text': 'example'}
        x = 0
        while x < 10:
            res = self.client.post('/labels/extract', data=data)
            self.assertEqual(res.status_code, 200)
            x += 1
        res = self.client.post('/labels/extract', data=data)
        self.assertEqual(res.status_code, 429)

if __name__ == '__main__':
    unittest.main()
