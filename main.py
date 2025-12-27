from browser import get_stealth_browser
from modules import glassdoor

def main():
    with get_stealth_browser() as browser:
        page = browser.page
        sb = browser.sb
        
        # Login
        glassdoor.login(page, sb, "amolmagar.connect@gmail.com", "Smartship@123")
        
        # Search jobs
        glassdoor.search_jobs(page, sb, "Software Engineer", "remote")
        
        # Extract and save data
        jobs_data = glassdoor.extract_jobs_data(page, sb)
        glassdoor.save_jobs_to_json(jobs_data, "glassdoor_jobs.json")
        print(f"✅ Saved {len(jobs_data)} jobs")

if __name__ == "__main__":
    main()
