from browser import get_stealth_browser

def main():
    with get_stealth_browser() as browser:
        page = browser.page
        sb = browser.sb
        
        page.goto("https://copilot.microsoft.com")
        page.wait_for_selector("textarea#userInput")
        sb.sleep(1)
        
        query = "Playwright Python connect_over_cdp() sync example"
        page.fill("textarea#userInput", query)
        page.click('button[data-testid="submit-button"]')
        
        sb.sleep(3)
        sb.solve_captcha()
        
        page.wait_for_selector('button[data-testid*="-thumbs-up"]', timeout=30000)
        sb.sleep(4)
        
        # Check if scroll button exists before clicking
        if page.locator('button[data-testid*="scroll-to-bottom"]').is_visible():
            page.click('button[data-testid*="scroll-to-bottom"]')
            sb.sleep(3)
            
        chat_results = '[data-testid="highlighted-chats"]'
        if page.locator(chat_results).is_visible():
            result = page.locator(chat_results).inner_text()
            print(result.replace("\n\n", " \n"))
        else:
            print("No results found or timed out.")

if __name__ == "__main__":
    main()