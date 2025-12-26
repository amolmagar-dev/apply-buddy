from contextlib import contextmanager
from playwright.sync_api import sync_playwright
from seleniumbase import sb_cdp

class StealthBrowser:
    def __init__(self, locale="en"):
        self.locale = locale
        self.sb = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def __enter__(self):
        # Initialize SeleniumBase in CDP mode (stealthy)
        self.sb = sb_cdp.Chrome(locale=self.locale)
        endpoint_url = self.sb.get_endpoint_url()

        # Connect Playwright to the CDP endpoint
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.connect_over_cdp(endpoint_url)
        self.context = self.browser.contexts[0]
        self.page = self.context.pages[0]
        
        # Return the object itself so we have access to .sb (for sleep/captcha) and .page
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        # sb_cdp Chrome instance doesn't have a strict 'quit' like WebDriver, 
        # but the process usually terminates. 
        # Explicit cleanup if needed would go here.

@contextmanager
def get_stealth_browser(locale="en"):
    """
    Context manager to easily get a stealthy page and the sb controller.
    Usage:
        with get_stealth_browser() as browser:
            browser.page.goto(...)
            browser.sb.sleep(1)
    """
    browser_manager = StealthBrowser(locale)
    try:
        yield browser_manager.__enter__()
    finally:
        browser_manager.__exit__(None, None, None)
