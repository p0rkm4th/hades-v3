import unittest
from playwright.sync_api import sync_playwright


class ComparisonUI(unittest.TestCase):
    def test_chat_form_keeps_internal_task_identity_hidden_and_shows_trial_metrics(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.route("**/api/turn", lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='{"text":"Your synthetic pantry has rice and milk.","task_id":"internal-only-task-id","tool_calls":["inventory_read"],"usage":{"prompt_tokens":19,"completion_tokens":8},"duration_ms":321}',
            ))
            page.goto("http://candidate-api:8080/")
            self.assertEqual(page.title(), "HADES Harness Comparison")
            self.assertEqual(
                page.get_by_label("Harness").locator("option").all_text_contents(),
                ["C — Lean loop", "A — Pydantic AI", "B — Reduced Hermes"],
            )
            page.get_by_label("Fixture user").select_option("amber")
            page.get_by_label("Harness").select_option("lean")
            page.get_by_label("Message").fill("What's in my kitchen?")
            page.get_by_role("button", name="Send").click()
            page.get_by_text("Your synthetic pantry has rice and milk.").wait_for()
            self.assertIn("321 ms · 1 tool calls · 27 model tokens", page.locator("#status").inner_text())
            self.assertNotIn("internal-only-task-id", page.locator("body").inner_text())
            browser.close()


if __name__ == "__main__":
    unittest.main()
