import json
from datetime import datetime

import os
import re

def get_session_filename(email):
    """Generates a safe session filename based on the email."""
    # Username is the part before the @
    username = email.split('@')[0]
    # Sanitize just in case
    safe_username = re.sub(r'[^a-zA-Z0-9_\-.]', '_', username)
    return f".session/glassdoor/{safe_username}/session.json"

def save_session(page, filename):
    """Saves the browser context storage state to a file."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        page.context.storage_state(path=filename)
        print(f"💾 Session saved to {filename}")
    except Exception as e:
        print(f"⚠️ Failed to save session: {e}")

def load_session(page, filename):
    """Loads the session from the file if it exists."""
    if os.path.exists(filename):
        try:
            # We need to reload cookies into the existing context
            with open(filename, 'r') as f:
                state = json.load(f)
                if "cookies" in state:
                    page.context.add_cookies(state["cookies"])
                    print(f"📂 Loaded session from {filename}")
                    return True
        except Exception as e:
            print(f"⚠️ Failed to load session: {e}")
    return False

def is_logged_in(page):
    """Checks if the user is logged in by verifying specific elements."""
    try:
        # Check for profile icon or absence of sign-in button
        # This selector depends on Glassdoor's specific DOM
        page.goto("https://www.glassdoor.co.in/member/home/index.htm")
        page.wait_for_load_state("domcontentloaded")
        
        # Check if redirected to login page
        if "login" in page.url or "signin" in page.url:
            return False
            
        return True
    except:
        return False

def login(page, sb, email, password):
    """Logs into Glassdoor using session or credentials."""
    session_file = get_session_filename(email)
    
    # 1. Try to load session
    if load_session(page, session_file):
        print("🔄 Verifying session...")
        if is_logged_in(page):
            print("✅ Session valid, skipping login")
            return
        else:
            print("❌ Session expired or invalid")
    
    print("🔑 Logging in with credentials...")
    page.goto("https://www.glassdoor.co.in/member/profile/login")
    page.wait_for_load_state("domcontentloaded")
    
    # Check if already logged in (redirected)
    if not ("login" in page.url or "signin" in page.url):
         print("✅ Already logged in (url check)")
         save_session(page, session_file)
         return

    try:
        page.get_by_role("textbox", name="Enter email").fill(email)
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded")
        
        # Check for password field
        try:
             page.get_by_role("textbox", name="Password").fill(password)
             page.keyboard.press("Enter")
             page.wait_for_load_state("domcontentloaded")
        except:
             print("⚠️ Password field not found immediately, checking if email only was needed or captcha flow")
        
        sb.sleep(3)
        
        # Verify login success
        if is_logged_in(page):
            print("✅ Login successful")
            save_session(page, session_file)
        else:
             print("⚠️ Login verification failed (might need manual check)")
             
    except Exception as e:
        print(f"❌ Login failed: {e}")


def search_jobs(page, sb, job_title, location):
    """Searches for jobs with the given title and location."""
    page.goto("https://www.glassdoor.co.in/Job/index.htm")
    page.wait_for_load_state("domcontentloaded")
    page.get_by_placeholder("Find your perfect job").fill(job_title)
    page.get_by_role("combobox", name="City, state, zipcode or \"remote\"").fill(location)
    page.keyboard.press("Enter")
    page.wait_for_load_state("domcontentloaded")
    sb.sleep(5)
    
    # SCROLL to load all jobs
    page.mouse.wheel(0, 800)
    sb.sleep(3)
    # Close job alert modal if present
    if page.locator('button[data-test="job-alert-modal-close"]').is_visible(timeout=2000):
        page.locator('button[data-test="job-alert-modal-close"]').click()

def extract_jobs_data(page, sb):
    """Extracts job data from the current page."""
    jobs = []
    
    job_selectors = [
        '[data-test="jobListing"]',
        '.JobsList_jobListItem__wjTHv',
        'li[data-jobid]',
    ]
    
    job_elements = None
    for selector in job_selectors:
        count = page.locator(selector).count()
        print(f"Selector '{selector}': {count}")
        if count > 0:
            job_elements = page.locator(selector)
            print(f"✅ Using: {selector}")
            break
    
    if not job_elements:
        return jobs
    
    total_jobs = min(job_elements.count(), 15)
    print(f"Processing {total_jobs} jobs...")
    
    for i in range(total_jobs):
        job_element = job_elements.nth(i)
        job_element.scroll_into_view_if_needed()
        sb.sleep(0.5)
        
        job_data = extract_single_job(job_element, i + 1)
        print(f"Job {i+1}: Title='{job_data['title'][:30]}' Company='{job_data['company'][:20]}'")
        
        if job_data["title"] or job_data["company"]:
            jobs.append(job_data)
    
    return jobs

def extract_single_job(job_element, index):
    """Extracts data for a single job element."""
    job_data = {
        "index": index, "job_id": "", "title": "", "company": "", 
        "location": "", "salary": "", "easy_apply": False, 
        "apply_link": "", "job_age": "", "scraped_at": datetime.now().isoformat()
    }
    
    # Job ID
    job_data["job_id"] = job_element.get_attribute("data-jobid") or ""
    
    # Title - multiple selectors
    title_selectors = [
        '[data-test="job-title"]',
        'a[data-test="job-title"]',
        '.JobCard_jobTitle__GLyJ1',
        'a.JobCard_jobTitle__GLyJ1',
        '.jobCard a[href*="/job-listing/"]'
    ]
    for selector in title_selectors:
        try:
            title_el = job_element.locator(selector).first
            if title_el.count() > 0:
                text = title_el.inner_text().strip()
                if text and len(text) > 5:
                    job_data["title"] = text
                    break
        except:
            continue
    
    # Company
    company_selectors = [
        '.EmployerProfile_compactEmployerName__9MGcV',
        '[class*="EmployerProfile"] span',
        '.compactEmployerName__9MGcV'
    ]
    for selector in company_selectors:
        try:
            company_el = job_element.locator(selector).first
            if company_el.count() > 0:
                text = company_el.inner_text().strip()
                if text and len(text) > 2:
                    job_data["company"] = text
                    break
        except:
            continue
    
    # Location
    try:
        loc_el = job_element.locator('[data-test="emp-location"], [id*="job-location"], [class*="location"]').first
        if loc_el.count() > 0:
            job_data["location"] = loc_el.inner_text().strip()
    except:
        pass
    
    # Salary
    try:
        sal_el = job_element.locator('[data-test="detailSalary"], [id*="salary"]').first
        if sal_el.count() > 0:
            job_data["salary"] = sal_el.inner_text().strip()
    except:
        pass
    
    # Easy Apply
    try:
        ea_el = job_element.locator('[aria-label="Easy Apply"], [class*="easyApply"]').first
        job_data["easy_apply"] = ea_el.is_visible(timeout=1000)
    except:
        pass
    
    # Link
    try:
        link_el = job_element.locator('a[href*="/job-listing/"], [data-test="job-link"]').first
        href = link_el.get_attribute("href")
        if href:
            job_data["apply_link"] = href if href.startswith("http") else f"https://www.glassdoor.co.in{href}"
    except:
        pass
    
    # Age
    try:
        age_el = job_element.locator('[data-test="job-age"], [class*="listingAge"]').first
        if age_el.count() > 0:
            job_data["job_age"] = age_el.inner_text().strip()
    except:
        pass
    
    return job_data

def save_jobs_to_json(jobs, filename):
    """Saves the extracted job data to a JSON file."""
    data = {
        "search_query": "Software Engineer remote",
        "total_jobs": len(jobs),
        "scraped_at": datetime.now().isoformat(),
        "jobs": jobs
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"📁 Saved to {filename}")

def apply_job(page, sb, job):
    """
    Applies to a single job.
    
    Args:
        page: The Playwright page object.
        sb: The stealth browser object (or similar helper).
        job: Dictionary containing job details (url, title, etc).
    """
    print(f"🚀 Starting application for: {job.get('title', 'Unknown Job')} at {job.get('company', 'Unknown Company')}")
    
    url = job.get("apply_link")
    if not url:
        print("❌ No apply link found for this job.")
        return

    try:
        page.goto(url)
        # using networkidle to ensure page is fully loaded (similar to networkidle2)
        page.wait_for_load_state("networkidle")
        sb.sleep(2) # Extra buffer
        print("✅ Navigated to job page")
        
        # Click Easy Apply
        # Selector provided: <button ... data-test="easyApply" ...>
        # Use specific selector to avoid strict mode violation (header vs mobile nav)
        apply_button = page.locator('[data-test="job-details-header"] [data-test="easyApply"]')
        
        # Fallback if header button not found (though unlikely on desktop view)
        if apply_button.count() == 0:
            apply_button = page.locator('button[data-test="easyApply"]').first
        
        if apply_button.is_visible():
            print("👇 Clicking 'Easy Apply' button...")
            
            # Check if clicking opens a new page (common in job boards)
            # We take a snapshot of pages before clicking
            context = page.context
            initial_pages = len(context.pages)
            
            apply_button.click()
            # sb.sleep() # Wait for potential redirect or new tab , can we make it dynamic
            page.wait_for_load_state("networkidle")
            sb.sleep(2) # Extra buffer

            
            current_pages = context.pages
            if len(current_pages) > initial_pages:
                new_page = current_pages[-1]
                handle_new_tab_application(new_page, sb)
            else:
                page.wait_for_load_state("networkidle")
                print("✅ Clicked Easy Apply (same page redirect)")
        else:
            print("❌ 'Easy Apply' button not found (possibly already applied or different flow)")

    except Exception as e:
        print(f"❌ Failed to navigate or click: {e}")

def handle_new_tab_application(new_page, sb):
    """
    Handles the application process when it opens in a new tab.
    """
    print("🔄 Handling new tab application...")
    try:
        new_page.wait_for_load_state("domcontentloaded")
        new_page.wait_for_load_state("networkidle") # Wait for redirects to finish
        sb.sleep(2)
        
        # Sometimes it stays on about:blank if we check too early
        if new_page.url == "about:blank":
             print("⚠️ URL is still about:blank, waiting longer...")
             new_page.wait_for_load_state("domcontentloaded")
             sb.sleep(3)
        
        print(f"✅ Application page ready: {new_page.url}")
        
        # Fill Address Details
        print("✍️ Filling address details...")
        
        # Handle page by URL - loop until application complete
        max_pages = 15
        last_url = ""
        
        for attempt in range(max_pages):
            try:
                # Check if tab is still open
                if new_page.is_closed():
                    print("⚠️ Tab was closed, moving to next job")
                    break
                    
                current_url = new_page.url
                print(f"🔍 Loop {attempt + 1}: URL = {current_url[:60]}...")
                
                # Check if we're done (success page)
                if "/applied" in current_url or "/success" in current_url or "/post-apply" in current_url:
                    print("🎉 Application completed!")
                    break
                
                # Skip if URL hasn't changed (wait for navigation)
                # if current_url == last_url:
                #     print(f"   ⏳ Same URL, waiting...")
                #     sb.sleep(1)
                #     continueß
                
                print(f"📍 Processing: {current_url.split('/')[-1]}")
                last_url = current_url
                handle_current_page_by_url(new_page, sb)
                
                # Wait for URL to change after action
                sb.sleep(3)
                
            except Exception as loop_error:
                print(f"⚠️ Loop error at attempt {attempt + 1}: {loop_error}")
                break
        
        print(f"🏁 Finished processing this job (loop ended)")
        
    except Exception as e:
        print(f"❌ Error in new tab: {e}")


def handle_current_page_by_url(page, sb):
    """Detects page type by URL path - 100% accurate"""
    if page.url == "about:blank":
        print("⚠️ URL is still about:blank, waiting longer...")
        sb.sleep(3)
        return  # Exit and let the loop retry
    
    current_url = page.url
    print(f"🌐 Current URL: {current_url}")
    
    # URL → Page Type mapping
    if "/resume-selection" in current_url:
        print("📄 Resume selection page")
        handle_indeed_resume(page, sb)
        
    elif "/resume-module/relevant-experience" in current_url:
        print("💼 Relevant experience page")
        handle_relevant_experience(page, sb)
        
    elif "/profile-location" in current_url:
        print("📍 Location page")
        handle_indeed_location(page, sb)
        
    elif "/questions" in current_url:
        print("❓ Questions page")
        handle_indeed_questions(page, sb)
        
    elif "/review" in current_url:
        print("📋 Review & Submit page")
        handle_review_submit(page, sb)
        
    elif "/post-apply" in current_url:
        print("🎉 POST-APPLY PAGE - Application submitted successfully!")
        handle_post_apply(page, sb)
        
    else:
        print("ℹ️ Unknown page - auto continue")
        pass


def handle_indeed_resume(page, sb):
    """Handles Indeed SmartApply Resume page"""
    
    print("📄 Indeed SmartApply Resume page")
    sb.sleep(1)
    
    # Click the radio INPUT directly (not the label)
    try:
        radio_input = page.get_by_test_id("resume-selection-file-resume-radio-card-input")
        radio_input.click(force=True)
        print("✅ Selected existing resume (radio input)")
    except:
        # Fallback: click the label
        resume_card = page.get_by_test_id("resume-selection-file-resume-radio-card-label")
        resume_card.scroll_into_view_if_needed()
        resume_card.click()
        print("✅ Selected existing resume (label)")
    
    sb.sleep(1)
    
    # Continue - store URL to verify navigation
    old_url = page.url
    page.get_by_test_id("continue-button").click()
    print("➡️ Clicked continue")
    
    # Wait for URL to change
    for _ in range(10):
        sb.sleep(0.5)
        if page.url != old_url:
            print(f"✅ Navigated to: {page.url}")
            break


def handle_indeed_location(page, sb):
    """Handles Indeed SmartApply Location page"""
    
    print("📍 Indeed SmartApply Location page")
    sb.sleep(1)
    
    # Fill ALL location fields with try/except to handle missing fields
    try:
        page.get_by_test_id("location-fields-postal-code-input").fill("411041")
        print("✅ Postal code: 411041")
    except:
        print("⚠️ Postal code field not found")
    
    try:
        page.get_by_test_id("location-fields-locality-input").fill("Pune, Maharashtra")
        print("✅ City/State: Pune, Maharashtra")
    except:
        print("⚠️ City/State field not found")
    
    try:
        page.get_by_test_id("location-fields-address-input").fill("Pune, India, 411041")
        print("✅ Address: Pune, India")
    except:
        print("⚠️ Address field not found")
    
    sb.sleep(1)
    
    # Continue - store URL to verify navigation
    old_url = page.url
    page.get_by_test_id("continue-button").click()
    print("➡️ Clicked continue")
    
    # Wait for URL to change
    for _ in range(10):
        sb.sleep(0.5)
        if page.url != old_url:
            print(f"✅ Navigated to: {page.url}")
            break


def handle_relevant_experience(page, sb):
    """Handles Indeed SmartApply Relevant Experience page"""
    
    print("💼 Indeed Relevant Experience page")
    sb.sleep(1)
    
    # Fill from resume data with try/except
    try:
        page.get_by_test_id("job-title-input").fill("SDE2")
        print("✅ Job title: SDE2")
    except:
        print("⚠️ Job title field not found")
    
    try:
        page.get_by_test_id("company-name-input").fill("SMART SHIP HUB DIGITAL INDIA PVT")
        print("✅ Company: SMART SHIP HUB DIGITAL INDIA PVT")
    except:
        print("⚠️ Company field not found")
    
    sb.sleep(1)
    
    # Continue - store URL to verify navigation
    old_url = page.url
    page.get_by_test_id("continue-button").click()
    print("➡️ Clicked continue")
    
    # Wait for URL to change
    for _ in range(10):
        sb.sleep(0.5)
        if page.url != old_url:
            print(f"✅ Navigated to: {page.url}")
            break


def handle_review_submit(page, sb):
    """Handles Indeed SmartApply Review & Submit page"""
    
    print("✅ Review page - Final submission!")
    
    # Scroll to bottom first
    page.mouse.wheel(0, 1000)
    sb.sleep(1)
    
    # Multiple selectors for Submit button
    submit_selectors = [
        'button:has-text("Submit your application")',
        '.css-140onwb:has-text("Submit your application")',
        'button span:has-text("Submit your application")',
        '[data-testid*="submit"]',
        'button[type="submit"]'
    ]
    
    for selector in submit_selectors:
        try:
            submit_btn = page.locator(selector).first
            if submit_btn.is_visible(timeout=3000):
                submit_btn.scroll_into_view_if_needed()
                submit_btn.click()
                print("🎉 SUBMITTED APPLICATION!")
                sb.sleep(3)
                return True
        except:
            continue
    
    print("⚠️ Submit button not found")
    return False


def handle_indeed_questions(page, sb):
    """Handles Indeed SmartApply Questions page - STUB for now"""
    
    print("❓ Questions page detected - TODO: implement question handling")
    
    # For now, just click continue
    try:
        page.get_by_test_id("continue-button").click()
        print("➡️ Skipped questions for now")
        sb.sleep(3)
    except:
        print("⚠️ Could not continue from questions page")


def handle_post_apply(page, sb):
    """Handles Indeed SmartApply Post-Apply page - Job successfully applied!"""
    
    print("🎉🎉🎉 APPLICATION SUBMITTED SUCCESSFULLY! 🎉🎉🎉")
    sb.sleep(2)
    
    # Close the tab since application is complete
    try:
        page.close()
        print("✅ Closed application tab")
    except:
        pass
