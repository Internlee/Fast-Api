from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

URL = (
    "https://in.indeed.com/jobs?q=job%20chennai"
    "&l=tamil%20nadu"
    "&sc=0kf%3Aattr(VDTG7)cmpsec(NKR5F)%3B"
    "&vjk=87f2815a8d4ca768"
)


def main() -> None:
    output_path = Path(__file__).with_name("source_html") / "indeed.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)
        try:
            page.wait_for_load_state("networkidle", timeout=45000)
        except PlaywrightTimeout:
            print("[Indeed] networkidle wait timed out; continuing")
        page.wait_for_timeout(5000)
        inner_html = page.inner_html("body")
        browser.close()

    soup = BeautifulSoup(inner_html, "html.parser")
    output_path.write_text(soup.prettify(), encoding="utf-8")
    print(f"Saved prettified HTML to {output_path}")


if __name__ == "__main__":
    main()
