import logging
import time

from playwright.sync_api import Playwright, TimeoutError as PlaywrightTimeout

from model.job import Job


unstop_logger = logging.getLogger("scraper.unstop")
internshala_logger = logging.getLogger("scraper.internshala")
naukri_logger = logging.getLogger("scraper.naukri")
glassdoor_logger = logging.getLogger("scraper.glassdoor")

MAX_LOAD_ATTEMPTS = 5
RETRY_DELAY_SECONDS = 3


def _load_until_visible(
    page,
    url: str,
    selector: str,
    logger: logging.Logger,
    label: str,
    *,
    timeout: int = 20000,
) -> bool:
    for attempt in range(1, MAX_LOAD_ATTEMPTS + 1):
        try:
            page.goto(url)
            page.wait_for_selector(selector, state="visible", timeout=timeout)
            if attempt > 1:
                logger.info("%s loaded on attempt %s", label, attempt)
            return True
        except PlaywrightTimeout:
            logger.warning(
                "%s attempt %s/%s timed out; retrying",
                label,
                attempt,
                MAX_LOAD_ATTEMPTS,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "%s attempt %s/%s failed: %s",
                label,
                attempt,
                MAX_LOAD_ATTEMPTS,
                exc,
            )
        time.sleep(RETRY_DELAY_SECONDS)
    logger.error("Unable to load %s after %s attempts", label, MAX_LOAD_ATTEMPTS)
    return False


def fetch_unstop(playwright:Playwright):
    addr = "https://unstop.com/internships?category=user-experience-ux-design%3Asoftware-development-engineering%3Amachine-learning-ai-engineering%3Adata-engineering-pipelines&oppstatus=open"
    base_url = "https://unstop.com"
    chromium = playwright.chromium
    browser = chromium.launch(headless=False)
    page = browser.new_page()
    if not _load_until_visible(
        page,
        addr,
        "a.item.position-relative",
        unstop_logger,
        "Unstop job cards",
        timeout=30000,
    ):
        browser.close()
        return []

    jobs = []  # Store all jobs
    unstop_logger.info("========== UNSTOP SCRAPE START ==========")
    blocks = page.locator("a.item.position-relative").all()
    if not blocks:
        unstop_logger.warning("Unstop returned 0 blocks; page structure might have changed")
    for block in blocks:
        link = block.get_attribute("href")
        if not link:
            continue
        content = block.locator("div.cptn")
        sections = content.locator("div").all()
        if len(sections) < 2:
            continue

        company_name = content.locator("p.single-wrap").text_content().strip()
        title = sections[0].text_content().strip()

        requirement_nodes = sections[1].locator("div").all()
        requirement_text = [req.text_content().strip() for req in requirement_nodes if req.text_content()]
        remaining = requirement_text.copy()

        def _extract(predicate) -> str | None:
            for idx, text in enumerate(remaining):
                if predicate(text.lower()):
                    return remaining.pop(idx)
            return None

        experience = _extract(lambda t: "experience" in t) or (
            remaining.pop(0) if remaining else "Experience not listed"
        )

        schedule_keywords = (
            "full time",
            "part time",
            "contract",
            "hybrid",
            "internship",
            "on field",
        )
        clocking = _extract(lambda t: any(k in t for k in schedule_keywords)) or (
            remaining.pop(0) if remaining else "Schedule not listed"
        )

        duration_keywords = ("month", "week", "day", "duration", "year")
        duration = _extract(lambda t: any(k in t for k in duration_keywords)) or "Duration not listed"

        location_keywords = (
            "remote",
            "office",
            "hybrid",
            "online",
            "onsite",
            "on-site",
            "india",
        )
        location = _extract(lambda t: any(k in t for k in location_keywords)) or (
            remaining.pop(0) if remaining else "Remote"
        )

        skills_text = content.locator("div.center-bullet.ng-star-inserted").all_inner_texts()
        skills = []
        if skills_text:
            skills = [skill.strip() for skill in skills_text[0].split("\n") if skill.strip()]

        job = Job(
            company=company_name,
            title=title,
            redirectLink=base_url + link,
            qualifications=skills,
            location=location,
            duration=duration,
            basedJob=clocking,
            experience=experience,
        )
        jobs.append(job)
        unstop_logger.info("- %s @ %s | %s", title, company_name, location)

    unstop_logger.info("========== UNSTOP SCRAPE END | %s jobs ==========", len(jobs))
    page.close()
    browser.close()

    return jobs

#TODO: To Include Pagination in This.

def fetch_internshala(playWRight:Playwright):
    addr = "https://internshala.com/internships/work-from-home-ai-agent-development,android-app-development,angular-js-development,artificial-intelligence-ai,backend-development,cloud-computing,computer-science,computer-vision,cyber-security,data-science,web-development,ios-app-development-internships/part-time-true/"
    base_url = "https://internshala.com"
    chromium = playWRight.chromium
    browser = chromium.launch(headless=True)
    page = browser.new_page()
    page.set_default_timeout(20000)

    resource_blocklist = {"image", "media", "font"}

    def _trim(text: str | None) -> str:
        return text.strip() if text else ""

    page.route(
        "**/*",
        lambda route: route.abort()
        if route.request.resource_type in resource_blocklist
        else route.continue_(),
    )

    internshala_logger.info("========== INTERNSHALA SCRAPE START ==========")
    if not _load_until_visible(
        page,
        addr,
        "div.individual_internship",
        internshala_logger,
        "Internshala cards",
        timeout=15000,
    ):
        browser.close()
        return []

    jobs = []
    model_subs = page.locator("div.modal.subscription_alert.new.show")
    if model_subs.is_visible():
        close_btn = model_subs.locator("#close_popup")
        if close_btn.count() > 0:
            close_btn.click()

    block_locator = page.locator(
        "div.container-fluid.individual_internship.view_detail_button.visibilityTrackerItem"
    )
    block_count = block_locator.count()
    internshala_logger.info("Internshala cards found: %s", block_count)

    for idx in range(block_count):
        block = block_locator.nth(idx)
        data_href = block.get_attribute("data-href") or ""
        link = base_url + data_href
        title = _trim(block.locator("h3.job-internship-name").text_content())
        company = _trim(block.locator("p.company-name").text_content())

        detail_row = block.locator("div.detail-row-1")
        divs = detail_row.locator("div").all()
        location = _trim(divs[0].text_content()) if len(divs) > 0 else "Remote"
        duration = _trim(divs[2].text_content()) if len(divs) > 2 else "Duration not listed"
        stipend = _trim(detail_row.locator("span.stipend").text_content())
        qualifications = _trim(block.locator("div.about_job").text_content())

        skill_nodes = block.locator("div.job_skills div.skill_container").all()
        skills = []
        for skill in skill_nodes:
            skill_text = _trim(skill.locator("div.job_skill").text_content())
            if skill_text:
                skills.append(skill_text)

        detail_row_2 = block.locator("div.detail-row-2")
        based = detail_row_2.locator("div.gray-labels div.status-li").all_inner_texts()
        based_job = based[0].strip() if based else "Schedule not listed"

        job = Job(
            company=company,
            title=title,
            redirectLink=link,
            qualifications=skills,
            location=location,
            duration=duration,
            basedJob=based_job,
            experience=qualifications,
            stipend=stipend,
        )
        jobs.append(job)
        internshala_logger.info("[%s/%s] %s @ %s", idx + 1, block_count, title, company)

    internshala_logger.info(
        "========== INTERNSHALA SCRAPE END | %s jobs ==========", len(jobs)
    )
    browser.close()
    return jobs

def fetch_naukri(playWirght:Playwright):
    addr = "https://www.naukri.com/internship-jobs-in-chennai?functionAreaIdGid=3&functionAreaIdGid=5&functionAreaIdGid=8&functionAreaIdGid=15"
    base_url = "https://www.naukri.com"
    chromium = playWirght.chromium
    browser = chromium.launch(headless=False)
    page = browser.new_page()
    if not _load_until_visible(
        page,
        addr,
        "div.styles_jlc__main__VdwtF",
        naukri_logger,
        "Naukri listings",
        timeout=20000,
    ):
        browser.close()
        return []

    jobs = []
    naukri_logger.info("========== NAUKRI SCRAPE START ==========")

    def _first_text(locator):
        if locator.count() == 0:
            return ""
        txt = locator.nth(0).text_content()
        return txt.strip() if txt else ""

    job_wrappers = page.locator("div.styles_jlc__main__VdwtF div.srp-jobtuple-wrapper")
    count = job_wrappers.count()
    if count == 0:
        naukri_logger.warning("Naukri returned 0 job cards; layout may have changed")
    else:
        naukri_logger.info("Naukri cards found: %s", count)

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
        naukri_logger.info(
            "[%s/%s] %s @ %s | %s | %s",
            idx + 1,
            count,
            title,
            company,
            location,
            stipend,
        )

    naukri_logger.info("========== NAUKRI SCRAPE END | %s jobs =========", len(jobs))
    browser.close()
    return jobs


def fetch_glassdoor(playwright: Playwright):
    addr = "https://www.glassdoor.co.in/Job/bengaluru-india-intern-jobs-SRCH_IL.0,15_IC2940587_KO16,22.htm?sgocId=1007&jobTypeIndeed=VDTG7"
    base_url = "https://www.glassdoor.co.in"
    chromium = playwright.chromium
    browser = chromium.launch(headless=False)
    page = browser.new_page()
    glassdoor_logger.info("========== GLASSDOOR SCRAPE START ==========")
    if not _load_until_visible(
        page,
        addr,
        "div#left-column",
        glassdoor_logger,
        "Glassdoor listings",
        timeout=20000,
    ):
        browser.close()
        return []

    def _text(locator, default="Not specified"):
        if locator.count() == 0:
            return default
        text = locator.nth(0).inner_text().strip()
        return text if text else default

    jobs = []
    job_cards = page.locator("div#left-column li[data-test='jobListing']")
    count = job_cards.count()
    if count == 0:
        glassdoor_logger.warning("Glassdoor returned 0 job cards; selector may be stale")
    else:
        glassdoor_logger.info("Glassdoor cards found: %s", count)

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
        glassdoor_logger.info(
            "[%s/%s] %s @ %s | %s",
            idx + 1,
            count,
            title,
            company,
            location,
        )
    browser.close()
    glassdoor_logger.info("========== GLASSDOOR SCRAPE END | %s jobs =========", len(jobs))
    return jobs
