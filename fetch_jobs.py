from playwright.sync_api import Playwright, TimeoutError as PlaywrightTimeout
from model.job import Job


def fetch_unstop(playwright:Playwright):
    addr = "https://unstop.com/internships?category=user-experience-ux-design%3Asoftware-development-engineering%3Amachine-learning-ai-engineering%3Adata-engineering-pipelines&oppstatus=open"
    base_url = "https://unstop.com"
    chromium = playwright.chromium
    browser = chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(addr)
    page.wait_for_load_state('networkidle')

    jobs = []  # Store all jobs
    print("----- It's unstop love -----")

    while True:
        
        blocks = page.locator("a.item.position-relative").all()
        for block in blocks:
            link = block.get_attribute("href")
            if link != None:
                content = block.locator("div.cptn")
                c = content.locator("div").all()
                if(len(c)==0):
                    continue
                companyName = content.locator("p.single-wrap").text_content()
                print(content.all_inner_texts())
                title = c[0].text_content()
                requirements = c[1].locator("div").all()
                experience = requirements[0].text_content()
                clocking = requirements[1].text_content()
                if len(requirements) != 3:
                    location = "Remote"
                else:    
                    location = requirements[2].text_content()
                skills = content.locator("div.center-bullet.ng-star-inserted").all_inner_texts()
                if len(skills) > 0:
                    skills = skills[0].split("\n")
                job = Job(company=companyName, title=title, redirectLink=base_url+link, qualifications=skills, location=location, duration="", basedJob=clocking, experience=experience)
                jobs.append(job) 
        print(f"Number of Jobs: {str(len(jobs))}") # Store the job
        page.locator("li.right-arrow.num.arrow.waves_effect:not(.ng-star-inserted)").click()
        
        # Wait for the skeleton to disappear and actual content to load
        #this line waits for the loading page to hide.
        page.wait_for_selector("app-global-skeleton", state="hidden", timeout=30000)
        # Also wait for the job cards to be visible
        #this line waits for the job cards to appear.
        page.wait_for_selector("div.panel_container a", state="visible", timeout=30000)
        page.wait_for_load_state("networkidle")
        endPage = page.locator("div.push-left.ng-star-inserted").all_text_contents()[0]
        endPage = endPage.split(" ")
        #ending page looks like this : ['', '55', '-', '72', '', '/', '115']
        if endPage[3] == endPage[6]:
            page.close()
            browser.close()
            break
        print(f"----- Parsing Complete: {len(jobs)} jobs found -----")
    browser.close()

    return jobs

#TODO: To Include Pagination in This.

def fetch_internshala(playWright:Playwright):
    ##phir btc pagination mein dikkat iski ma ka !!!
    addr = "https://internshala.com/internships/work-from-home-ai-agent-development,android-app-development,angular-js-development,artificial-intelligence-ai,backend-development,cloud-computing,computer-science,computer-vision,cyber-security,data-science,web-development,ios-app-development-internships/part-time-true/"
    base_url = "https://internshala.com"
    chromium = playWright.chromium
    browser = chromium.launch(headless=False)
    pg = 1
    page = browser.new_page()
    page.goto(addr)
    try:
        page.wait_for_load_state("networkidle", timeout=45000)
    except PlaywrightTimeout:
        print("[Glassdoor] networkidle wait timed out, continuing with available content")
    model_subs = page.locator("div.modal.subscription_alert.new.show")
    jobs = []
    if model_subs.is_visible():
        close = page.locator("#close_popup")
        close.click()
    page.wait_for_selector("div.individual_internship", state="visible", timeout=10000)
    
    print("--- Scraping Process start ---")
    internship_block = page.locator("div.internship_list_container")
    di = internship_block.locator("div")
    blocks = di.locator("div.container-fluid.individual_internship.view_detail_button.visibilityTrackerItem")
    block_count = blocks.count()
    print(f"Found {block_count} blocks")
    
    for idx in range(block_count):
        block = blocks.nth(idx)
        link = base_url + block.get_attribute("data-href")
        title = block.locator("h3.job-internship-name").text_content().strip()
        company = block.locator("p.company-name").text_content().strip()
        detail_row = block.locator("div.detail-row-1")
        divs = detail_row.locator("div").all()
        location = divs[0].text_content().strip()
        stipend = detail_row.locator("span.stipend").text_content().strip()
        duration = divs[2].text_content().strip()
        qualifications = block.locator("div.about_job").text_content().strip()
        skills = block.locator("div.job_skills").locator("div.skill_container").all()
        ski = []

        detail_row_2 = block.locator("div.detail-row-2")
        based = detail_row_2.locator("div.gray-labels").locator("div.status-li").all_inner_texts()

        for skill in skills:
            ski.append(skill.locator("div.job_skill").text_content())
        job = Job(company=company,
                  title=title,
                  redirectLink=link,
                  qualifications=ski,
                  location=location,
                  duration=duration,
                  basedJob=based[0],
                  experience=qualifications,
                  stipend=stipend)
        jobs.append(job)
        print(f"id: {idx} | title : {title}")
    
    print(f"--- Scraping Complete: {len(jobs)} jobs found ---")
    browser.close()
    return jobs

def fetch_naukri(playWirght:Playwright):
    addr = "https://www.naukri.com/internship-jobs-in-chennai?functionAreaIdGid=3&functionAreaIdGid=5&functionAreaIdGid=8&functionAreaIdGid=15"
    base_url = "https://www.naukri.com"
    chromium = playWirght.chromium
    browser = chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(addr)
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("div.styles_jlc__main__VdwtF", state="visible", timeout=20000)

    jobs = []

    def _first_text(locator):
        if locator.count() == 0:
            return ""
        txt = locator.nth(0).text_content()
        return txt.strip() if txt else ""

    job_wrappers = page.locator("div.styles_jlc__main__VdwtF div.srp-jobtuple-wrapper")
    count = job_wrappers.count()
    print(f"--- Found {count} Naukri cards ---")

    for idx in range(count):
        wrapper = job_wrappers.nth(idx)
        card = wrapper.locator("div.cust-job-tuple.layout-wrapper")
        if card.count() == 0:
            continue

        title_anchor = card.locator("a.title")
        if title_anchor.count() == 0:
            continue
        title = _first_text(title_anchor)
        link = title_anchor.nth(0).get_attribute("href") if title else None
        if not title or not link:
            continue

        company = _first_text(card.locator("span.comp-dtls-wrap a.comp-name")) or "Not specified"
        duration = _first_text(card.locator("span.exp-wrap span[title]")) or "Not specified"
        stipend = _first_text(card.locator("span.sal-wrap span[title]")) or "Not specified"
        location = _first_text(card.locator("span.loc-wrap span[title]")) or "Not specified"
        based_job = _first_text(card.locator("span.job-post-day")) or "Schedule not listed"

        qualifications = [text.strip() for text in card.locator("div.tuple-tags-container *").all_inner_texts() if text.strip()]
        if not qualifications:
            qualifications = [text.strip() for text in card.locator("div.row5 li").all_inner_texts() if text.strip()]

        experience_detail = " | ".join([text.strip() for text in card.locator("div.row4 li").all_inner_texts() if text.strip()])
        experience = experience_detail or "Not specified"

        job = Job(
            company=company,
            title=title,
            redirectLink=link if link.startswith("http") else base_url + link,
            qualifications=qualifications,
            location=location,
            duration=duration,
            basedJob=based_job,
            experience=experience,
            stipend=stipend
        )
        jobs.append(job)
        print(f"[{idx}] {title} @ {company} @ {stipend} @ {experience} @ {duration}")

    browser.close()
    return jobs


def fetch_glassdoor(playwright: Playwright):
    addr = "https://www.glassdoor.co.in/Job/bengaluru-india-intern-jobs-SRCH_IL.0,15_IC2940587_KO16,22.htm?sgocId=1007&jobTypeIndeed=VDTG7"
    base_url = "https://www.glassdoor.co.in"
    chromium = playwright.chromium
    browser = chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(addr)
    try:
        page.wait_for_load_state("networkidle", timeout=45000)
    except PlaywrightTimeout:
        print("[Glassdoor] networkidle wait timed out, continuing with available content")
    page.wait_for_selector("div#left-column", state="visible", timeout=20000)

    def _text(locator, default="Not specified"):
        if locator.count() == 0:
            return default
        text = locator.nth(0).inner_text().strip()
        return text if text else default

    jobs = []
    job_cards = page.locator("div#left-column li[data-test='jobListing']")
    count = job_cards.count()
    print(f"--- Found {count} Glassdoor cards ---")

    for idx in range(count):
        card = job_cards.nth(idx)
        title_locator = card.locator("a.JobCard_jobTitle__GLyJ1")
        title = _text(title_locator, default="")
        link = title_locator.get_attribute("href") if title else None
        if not title or not link:
            continue
        link = base_url + link if link.startswith("/") else link

        company = _text(card.locator("span.EmployerProfile_compactEmployerName__9MGcV"))
        location = _text(card.locator("div[data-test='emp-location']"))
        stipend = _text(card.locator("div[data-test='detailSalary']"))
        posting_age = _text(card.locator("div.JobCard_listingAge__jJsuc"), default="Posting age NA")

        snippet_lines = [text.strip() for text in card.locator("div.JobCard_jobDescriptionSnippet__l1tnl div").all_inner_texts() if text.strip()]
        experience = snippet_lines[0] if snippet_lines else "Not specified"
        qualifications = []
        for line in snippet_lines:
            lowered = line.lower()
            if lowered.startswith("skills"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    qualifications = [skill.strip() for skill in parts[1].split(",") if skill.strip()]
                break

        job = Job(
            company=company,
            title=title,
            redirectLink=link,
            qualifications=qualifications,
            location=location,
            duration="Not specified",
            basedJob=posting_age,
            experience=experience,
            stipend=stipend or "check source site"
        )
        jobs.append(job)
    browser.close()
    return jobs
