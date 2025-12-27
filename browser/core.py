from contextlib import contextmanager
from playwright.sync_api import sync_playwright
from seleniumbase import sb_cdp

class StealthPage:
    """
    Wrapper around Playwright Page object.
    Intercepts interactive methods to scan for iframes and solve captchas before proceeding.
    """
    def __init__(self, page, sb):
        self._page = page
        self._sb = sb

    def __getattr__(self, name):
        attr = getattr(self._page, name)
        
        # If the attribute is not callable (like a property), return it directly
        if not callable(attr):
            return attr
            
        # List of interactive methods to intercept
        # We trigger captcha checks before these actions
        action_methods = ['click', 'fill', 'type', 'press', 'check', 'uncheck', 'select_option']
        
        # List of wait methods to intercept
        # We will loop these to scan for captchas continuously
        wait_methods = ['wait_for_selector', 'wait_for_function', 'wait_for_timeout', 'wait_for_load_state']

        def check_and_solve_captcha():
            # Check for:
            # 1. Any visible iframe (standard check)
            # 2. Known Turnstile container #cf-turnstile (handle closed shadow roots)
            iframe_visible = self._page.locator("iframe:visible").count() > 0
            turnstile_present = self._page.locator("#cf-turnstile").count() > 0
            
            if iframe_visible or turnstile_present:
                print(f"[StealthPage] Potential captcha detected (Iframe: {iframe_visible}, Turnstile: {turnstile_present}). Solving...")
                try:
                    self._sb.solve_captcha()
                except Exception as e:
                    print(f"Warning: solve_captcha failed: {e}")

        if name in action_methods:
            def wrapper(*args, **kwargs):
                check_and_solve_captcha()
                return attr(*args, **kwargs)
            return wrapper

        if name in wait_methods:
            def wrapper(*args, **kwargs):
                check_and_solve_captcha()
                
                # Special handling for wait_for_selector to support "scanning while waiting"
                if name == 'wait_for_selector':
                    selector = args[0] if len(args) > 0 else kwargs.get('selector')
                    timeout = kwargs.get('timeout', 30000) # default standard 30s
                    
                    if selector and timeout > 2000:
                        # Break it down into chunks
                        # We'll try in 2s increments
                        import time
                        start_time = time.time()
                        while (time.time() - start_time) * 1000 < timeout:
                            try:
                                # Try waiting for a short duration
                                return attr(selector, timeout=2000, state=kwargs.get('state'), strict=kwargs.get('strict'))
                            except Exception:
                                # Timeout, check captcha again
                                check_and_solve_captcha()
                                # If total time exceeded, break and let the final call raise or fail
                                if (time.time() - start_time) * 1000 >= timeout:
                                    break
                        # One final try with remaining time (or 0) to raise the proper error
                        remaining = max(0, timeout - (time.time() - start_time) * 1000)
                        return attr(*args, **{**kwargs, 'timeout': remaining})

                return attr(*args, **kwargs)
            return wrapper
        
        return attr

class StealthBrowser:
    def __init__(self, locale="en"):
        self.locale = locale
        self.sb = None
        self.playwright = None
        self.browser = None
        self.context = None
        self._raw_page = None
        self.page = None

    def __enter__(self):
        # Initialize SeleniumBase in CDP mode (stealthy)
        self.sb = sb_cdp.Chrome(locale=self.locale)
        endpoint_url = self.sb.get_endpoint_url()

        # Connect Playwright to the CDP endpoint
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.connect_over_cdp(endpoint_url)
        self.context = self.browser.contexts[0]
        self._raw_page = self.context.pages[0]
        
        # Wrap the page to add auto-captcha handling
        self.page = StealthPage(self._raw_page, self.sb)
        
        # Return the object itself
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        # sb_cdp Chrome instance doesn't have a strict 'quit' like WebDriver, 
        # but the process usually terminates. 

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
