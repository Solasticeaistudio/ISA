import unittest
from unittest.mock import patch

import app as app_module


class ChatClarificationRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_chat_asks_for_model_before_retrieval(self):
        with patch.object(app_module.config, "missing_required_env", return_value=[]), patch.object(
            app_module, "retrieve_context"
        ) as retrieve_context:
            response = self.client.post(
                "/api/chat",
                json={
                    "message": "What does this alarm mean?",
                    "product": "All Products",
                    "category": "All Categories",
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["needs_clarification"])
        self.assertEqual(data["citations"], [])
        self.assertIn("provide the Inogen model", data["answer"])
        retrieve_context.assert_not_called()

    def test_chat_retrieves_when_product_is_selected(self):
        with patch.object(app_module.config, "missing_required_env", return_value=[]), patch.object(
            app_module, "retrieve_context", return_value=[]
        ) as retrieve_context:
            response = self.client.post(
                "/api/chat",
                json={
                    "message": "What does this alarm mean?",
                    "product": "Rove 6",
                    "category": "All Categories",
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertNotIn("needs_clarification", data)
        retrieve_context.assert_called_once()


if __name__ == "__main__":
    unittest.main()
