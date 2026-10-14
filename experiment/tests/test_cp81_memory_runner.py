import unittest

from run_cp81_memory_case import CASES, answer_matches, candidate_error_category


class Cp81MemoryAnswerOracleTests(unittest.TestCase):
    def test_positive_synthetic_answers(self):
        self.assertTrue(answer_matches("Confirmed: light roast.", CASES["coffee_scalar"]))
        self.assertTrue(answer_matches("Use a concise numbered checklist.", CASES["weekly_structured"]))
        self.assertTrue(answer_matches("Late afternoon on weekdays.", CASES["reminder_list"]))

    def test_negated_synthetic_answers_fail(self):
        self.assertFalse(answer_matches("Your preference is not light roast.", CASES["coffee_scalar"]))
        self.assertFalse(answer_matches("Do not use a concise numbered checklist.", CASES["weekly_structured"]))
        self.assertFalse(answer_matches("Not late afternoon; use mornings.", CASES["reminder_list"]))

    def test_partial_list_answer_fails(self):
        self.assertFalse(answer_matches("Late afternoon, but not weekdays.", CASES["reminder_list"]))

    def test_candidate_failures_are_sanitized_and_classified(self):
        self.assertEqual(candidate_error_category(0, {"transport_error_type": "TimeoutError"}), "transport_error")
        self.assertEqual(candidate_error_category(400, {"error": "private provider detail"}), "http_400")
        self.assertEqual(candidate_error_category(502, {"error": "provider rejected request"}), "http_502")
        self.assertEqual(candidate_error_category(200, {"error": "candidate failure"}), "candidate_reported_error")
        self.assertEqual(candidate_error_category(200, {"invalid_json_response": True}), "invalid_json_response")


if __name__ == "__main__":
    unittest.main()
