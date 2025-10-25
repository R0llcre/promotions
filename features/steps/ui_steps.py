"""Step definitions for the Admin UI BDD smoke test.

All interactions are performed via the browser (Selenium) against the UI
at /ui. No direct API calls are made in these steps.
"""

from behave import given, then
from selenium.webdriver.common.by import By


@given("the Promotions UI is available")
def step_ui_is_available(context):
    """Navigate to the /ui page and ensure basic content is present."""
    context.browser.get(context.base_url + "/ui")
    title = context.browser.title or ""
    page = context.browser.page_source or ""
    assert "Promotions Admin" in title or "Promotions Admin" in page


@then('the page title contains "{text}"')
def step_title_contains(context, text):
    """Assert that the document.title contains a specific substring."""
    assert text in (context.browser.title or "")
    # Also ensure our H1 is present for robustness
    h1 = context.browser.find_element(By.ID, "title")
    assert text in h1.text
