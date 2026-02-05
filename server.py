import asyncio
import contextlib
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, List, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from playwright.sync_api import sync_playwright
from supabase import Client, create_client

from fetch_jobs import (
    fetch_glassdoor,
    fetch_internshala,
    fetch_naukri,
    fetch_unstop,
)
from model.job import Job

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("job-service")

Scraper = Callable[[Any], List[Job]]
SCRAPE_INTERVAL_SECONDS = int(os.getenv("SCRAPE_INTERVAL_SECONDS", str(60 * 60 * 24)))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "internships")

JOB_SOURCES: Tuple[Tuple[str, Scraper], ...] = (
    ("unstop", fetch_unstop),
    ("internshala", fetch_internshala),
    ("naukri", fetch_naukri),
    ("glassdoor", fetch_glassdoor),
)

app = FastAPI(title="Internlee Scraper Service")
supabase_client: Client | None = None
scrape_lock = asyncio.Lock()
status_snapshot = {
    "last_run_started": None,
    "last_run_finished": None,
    "last_status": "never",
    "last_error": None,
    "last_count": 0,
}


def init_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase credentials are missing. Check .env values.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def chunked(items: Iterable[dict], size: int = 100) -> Iterable[List[dict]]:
    chunk: List[dict] = []
    for item in items:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def job_to_record(job: Job) -> dict:
    return {
        "company": job.company,
        "title": job.title,
        "redirect_link": job.redirectLink,
        "qualifications": job.qualifications or [],
        "location": job.location,
        "duration": job.duration,
        "based_job": job.basedJob,
        "experience": job.experience,
        "stipend": job.stipend,
    }


def replace_supabase_rows(client: Client, records: List[dict]) -> None:
    logger.info("Clearing existing rows in %s", SUPABASE_TABLE)
    client.table(SUPABASE_TABLE).delete().neq("id", 0).execute()
    if not records:
        logger.info("No new jobs to insert after clearing table")
        return
    for batch in chunked(records, size=50):
        client.table(SUPABASE_TABLE).insert(batch).execute()
        logger.info("Inserted %s records", len(batch))


def run_full_scrape(triggered_by: str) -> int:
    logger.info("Starting scrape run triggered by %s", triggered_by)
    total_jobs: List[Job] = []
    with sync_playwright() as playwright:
        for source_name, scraper in JOB_SOURCES:
            start = time.perf_counter()
            logger.info("[%s] Fetch start", source_name)
            try:
                jobs = scraper(playwright)
                total_jobs.extend(jobs)
                elapsed = time.perf_counter() - start
                logger.info("[%s] Fetch complete | %s jobs | %.2fs", source_name, len(jobs), elapsed)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("[%s] Fetch failed: %s", source_name, exc)
                raise
    if supabase_client is None:
        raise RuntimeError("Supabase client is not initialized")
    replace_supabase_rows(supabase_client, [job_to_record(job) for job in total_jobs])
    logger.info("Scrape run finished. Total jobs: %s", len(total_jobs))
    return len(total_jobs)


async def trigger_scrape(triggered_by: str) -> JSONResponse:
    if scrape_lock.locked():
        raise HTTPException(status_code=409, detail="Scraper already running")
    async with scrape_lock:
        status_snapshot["last_run_started"] = datetime.now(timezone.utc).isoformat()
        status_snapshot["last_status"] = "running"
        status_snapshot["last_error"] = None
        try:
            job_count = await asyncio.to_thread(run_full_scrape, triggered_by)
        except Exception as exc:  # pylint: disable=broad-except
            status_snapshot["last_status"] = "error"
            status_snapshot["last_error"] = str(exc)
            status_snapshot["last_run_finished"] = datetime.now(timezone.utc).isoformat()
            logger.error("Scrape run crashed: %s", exc)
            raise
        status_snapshot["last_status"] = "ok"
        status_snapshot["last_run_finished"] = datetime.now(timezone.utc).isoformat()
        status_snapshot["last_count"] = job_count
        return JSONResponse({"status": "ok", "count": job_count})


async def scheduler_loop() -> None:
    await asyncio.sleep(5)
    while True:
        try:
            await trigger_scrape("scheduler")
        except HTTPException as exc:
            logger.warning("Scheduler trigger failed with HTTPException: %s", exc.detail)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Scheduler run failed: %s", exc)
        await asyncio.sleep(SCRAPE_INTERVAL_SECONDS)


@app.on_event("startup")
async def on_startup() -> None:
    global supabase_client  # pylint: disable=global-statement
    supabase_client = init_supabase()
    logger.info("Supabase client initialized")
    app.state.scheduler_task = asyncio.create_task(scheduler_loop())
    logger.info(
        "Scheduler started with %s second interval",
        SCRAPE_INTERVAL_SECONDS,
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    task: asyncio.Task | None = getattr(app.state, "scheduler_task", None)
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@app.get("/health")
async def health() -> dict:
    return {
        "status": status_snapshot["last_status"],
        "last_run_started": status_snapshot["last_run_started"],
        "last_run_finished": status_snapshot["last_run_finished"],
        "last_error": status_snapshot["last_error"],
    }


@app.get("/jobs/last-run")
async def last_run() -> dict:
    return status_snapshot


@app.post("/jobs/refresh")
async def manual_refresh() -> JSONResponse:
    return await trigger_scrape("manual")
