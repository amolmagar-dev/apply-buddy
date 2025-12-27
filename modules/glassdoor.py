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
