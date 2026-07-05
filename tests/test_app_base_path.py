import unittest
from unittest import mock

import config
from app import app


class BasePathRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_index_uses_forwarded_prefix(self):
        with mock.patch.object(config, "ISA_BASE_PATH", ""):
            response = self.client.get("/", headers={"X-Forwarded-Prefix": "/isa"})

        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('/isa/static/css/style.css', html)
        self.assertIn('window.ISA_BASE_PATH = "/isa";', html)

    def test_index_still_works_at_root(self):
        with mock.patch.object(config, "ISA_BASE_PATH", ""):
            response = self.client.get("/")

        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('/static/css/style.css', html)
        self.assertIn('window.ISA_BASE_PATH = "";', html)


if __name__ == "__main__":
    unittest.main()
