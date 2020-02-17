import json
import unittest
import sys
sys.path.append('/app')

from tipi_backend.app import create_app
from tipi_backend.settings import Config


class TestLimit(unittest.TestCase):

    def setUp(self):
        Config.TESTING = True
        Config.USE_ALERTS = True
        app = create_app(config=Config)
        self.client = app.test_client()

    def test_limit_each_call(self):
        x = 0
        data = json.dumps({'email': 'foo@bar.com', 'search': '{"topic": "bar"}'})
        while x < 10:
            # labeling
            res = self.client.post('/labels/extract', data={'text': 'example'})
            self.assertEqual(res.status_code, 200)
            # alerts
            res = self.client.post('/alerts', data=data, content_type='application/json')
            self.assertEqual(res.status_code, 200)
            x += 1
        res = self.client.post('/alerts', data=data, content_type='application/json')
        self.assertEqual(res.status_code, 429)

if __name__ == '__main__':
    unittest.main()
