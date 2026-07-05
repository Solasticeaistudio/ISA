import unittest

from rag.clarification import mentioned_products, should_ask_for_model


class ClarificationTests(unittest.TestCase):
    def test_generic_column_question_needs_model(self):
        self.assertTrue(should_ask_for_model("How do I replace the columns?", "All Products"))

    def test_generic_battery_question_needs_model(self):
        self.assertTrue(should_ask_for_model("Why won't my battery charge?", "All Products"))

    def test_generic_alarm_question_needs_model(self):
        self.assertTrue(should_ask_for_model("What does this alarm mean?", "All Products"))

    def test_generic_faa_question_needs_model(self):
        self.assertTrue(should_ask_for_model("Is this device FAA approved?", "All Products"))

    def test_selected_product_does_not_need_model(self):
        self.assertFalse(should_ask_for_model("Why won't my battery charge?", "Rove 6"))

    def test_question_with_model_does_not_need_clarification(self):
        self.assertFalse(should_ask_for_model("How do I replace the columns on a Rove 6?", "All Products"))

    def test_compare_specific_models_does_not_need_clarification(self):
        self.assertFalse(should_ask_for_model("Compare the Rove 6 and G5.", "All Products"))

    def test_broad_model_question_does_not_need_clarification(self):
        self.assertFalse(should_ask_for_model("Which models are FAA approved?", "All Products"))

    def test_non_product_question_does_not_need_clarification(self):
        self.assertFalse(should_ask_for_model("Who are you?", "All Products"))

    def test_detects_compact_model_names(self):
        self.assertIn("Rove 6", mentioned_products("Is Rove6 FAA approved?"))
        self.assertIn("G5", mentioned_products("What does the G5 alarm mean?"))


if __name__ == "__main__":
    unittest.main()
