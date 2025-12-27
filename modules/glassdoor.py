import json
from datetime import datetime

def login(page, sb, email, password):
    """Logs into Glassdoor using the provided credentials."""
    page.goto("https://www.glassdoor.co.in/index.htm")
    page.wait_for_load_state("domcontentloaded")
    page.get_by_role("textbox", name="Enter email").fill(email)
    page.keyboard.press("Enter")
    page.wait_for_load_state("domcontentloaded")
    page.get_by_role("textbox", name="Password").fill(password)
    page.keyboard.press("Enter")
    page.wait_for_load_state("domcontentloaded")
    sb.sleep(3)

def search_jobs(page, sb, job_title, location):
    """Searches for jobs with the given title and location."""
    page.goto("https://www.glassdoor.co.in/Job/index.htm")
    page.wait_for_load_state("domcontentloaded")
    page.get_by_placeholder("Find your perfect job").fill(job_title)
    page.get_by_role("combobox", name="City, state, zipcode or \"remote\"").fill(location)
    page.keyboard.press("Enter")
    page.wait_for_load_state("networkidle")
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
            sb.sleep(3) # Wait for potential redirect or new tab
            
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
             sb.sleep(3)
        
        print(f"✅ Application page ready: {new_page.url}")
        
        # Fill Address Details
        print("✍️ Filling address details...")
        
        # Handle page by URL - loop until application complete
        max_pages = 10
        for _ in range(max_pages):
            handle_current_page_by_url(new_page, sb)
            sb.sleep(2)
            
            # Check if we're done (success page or closed)
            if "/applied" in new_page.url or "/success" in new_page.url:
                print("🎉 Application completed!")
                break
        
    except Exception as e:
        print(f"❌ Error in new tab: {e}")


def handle_current_page_by_url(page, sb):
    """Detects page type by URL path - 100% accurate"""
    
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
        
    else:
        print("ℹ️ Unknown page - auto continue")
        try:
            page.get_by_test_id("continue-button").click()
            sb.sleep(2)
        except:
            pass


def handle_indeed_resume(page, sb):
    """Handles Indeed SmartApply Resume page"""
    
    # Wait for resume page
    page.wait_for_selector('#mosaic-provider-module-apply-resume-selection', timeout=10000)
    print("📄 Indeed SmartApply Resume page")
    
    # Select EXISTING resume (already uploaded)
    resume_card = page.get_by_test_id("resume-selection-file-resume-radio-card-label")
    resume_card.scroll_into_view_if_needed()
    resume_card.click()
    print("✅ Selected existing resume")
    
    # Continue
    page.get_by_test_id("continue-button").click()
    print("➡️ Continued to next step")
    sb.sleep(3)


def handle_indeed_location(page, sb):
    """Handles Indeed SmartApply Location page"""
    
    # Wait for location page
    page.wait_for_selector('#mosaic-provider-module-apply-contact-info', timeout=10000)
    print("📍 Indeed SmartApply Location page")
    
    # Fill ALL location fields
    page.get_by_test_id("location-fields-postal-code-input").fill("411041")
    print("✅ Postal code: 411041")
    
    page.get_by_test_id("location-fields-locality-input").fill("Pune, Maharashtra")
    print("✅ City/State: Pune, Maharashtra")
    
    page.get_by_test_id("location-fields-address-input").fill("Pune, India, 411041")
    print("✅ Address: Pune, India")
    
    # Continue
    page.get_by_test_id("continue-button").click()
    print("➡️ Continued")
    sb.sleep(3)


def handle_relevant_experience(page, sb):
    """Handles Indeed SmartApply Relevant Experience page"""
    
    # Wait for relevant experience page
    page.wait_for_selector('#mosaic-provider-module-apply-resume', timeout=10000)
    print("💼 Indeed Relevant Experience page")
    
    # Fill from resume data
    page.get_by_test_id("job-title-input").fill("SDE2")
    print("✅ Job title: SDE2")
    
    page.get_by_test_id("company-name-input").fill("SMART SHIP HUB DIGITAL INDIA PVT")
    print("✅ Company: SMART SHIP HUB DIGITAL INDIA PVT")
    
    # Continue
    page.get_by_test_id("continue-button").click()
    print("➡️ Continued")
    sb.sleep(3)


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
