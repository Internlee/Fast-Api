from playwright.sync_api import Playwright,sync_playwright
from fetch_jobs import fetch_unstop,fetch_internshala,fetch_naukri,fetch_glassdoor
from model.job import Job

#finally this shit is working, i even tried selenium for swiggy careers and it wasn't working,so switched to playwright and google jobs for now
#Will extract everything else after setting up the whole ecosystem once.

def fetch_google(playWright: Playwright):
    #i need to update this ... 
    start_url = "https://www.google.com/about/careers/applications/jobs/results?employment_type=INTERN&employment_type=TEMPORARY&employment_type=PART_TIME&employment_type=FULL_TIME&degree=MASTERS&degree=PURSUING_DEGREE&degree=BACHELORS&sort_by=date&company=GFiber&company=Wing&company=Verily%20Life%20Sciences&company=YouTube&company=Waymo&company=Google&target_level=MID&target_level=EARLY&target_level=INTERN_AND_APPRENTICE#!t=jo&jid=127025001"
    base_url = "https://www.google.com/about/careers/applications/"
    chrome = playWright.chromium
    browser = chrome.launch(headless=True)
    page = browser.new_page()
    page.goto(start_url)
    page.wait_for_load_state("networkidle")
    while True:
        while True:
            pageNumberList = page.locator("div.VfPpkd-wZVHld-gruSEe-j4LONd").text_content().split(" ")
            startingIdx = pageNumberList[0].split("‑")[1]
            print(pageNumberList)

            title = []
            qual = []
            locations = []
            redirectUri = []

            #title
            for tit in page.locator("h3.QJPWVe").all_text_contents():
                title.append(tit)

            #qualifications
            for q in page.locator("div.Xsxa1e").all_text_contents():
                qual.append(q)
            #locations

            for l in page.locator("span.r0wTof").all_text_contents():
                locations.append(l)

            if(startingIdx == pageNumberList[2]):
                print("Finish")
                page.close()
                browser.close()
                break
            
            for link in page.locator("a.WpHeLc.VfPpkd-mRLv6.VfPpkd-RLmnJb").all():
                url = link.get_attribute("href")
                redirectUri.append(base_url+url)
            jobs :list[Job] = []
            for i,tit in enumerate(title):
                job = Job(jobId= i,locations=locations[i],title=tit,qualifications=qual[i],company="Google",redirectLink=redirectUri[i])
                jobs.append(job)
            nextUrl = page.get_by_role("link", name="Go to next page").get_attribute("href")
            page.goto(nextUrl)
            page.wait_for_load_state("networkidle")

        browser.close()

with sync_playwright() as playwright:
    fetch_unstop(playwright)
