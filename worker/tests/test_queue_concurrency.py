"""
Regression tests for D7 — atomic SQLite job claiming.

Verifies that concurrent consumers cannot double-claim the same job
under SQLite (no SKIP LOCKED). Uses independent engine connections
per consumer thread to reproduce real race conditions.
"""
from __future__ import annotations

import threading
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Asset, ScanJob
from worker import queue as worker_queue


@pytest.fixture()
def sqlite_file(tmp_path):
    """File-backed SQLite DB (same engine style as production worker)."""
    db_path = tmp_path / "claim_test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


def _make_session(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)()


def _insert_asset_and_jobs(engine, count: int) -> list[int]:
    session = _make_session(engine)
    asset = Asset(
        name="Claim Test Asset",
        target_ip="127.0.0.1",
        port=80,
        status="UNKNOWN",
        availability_status="UNKNOWN",
    )
    session.add(asset)
    session.flush()
    ids = []
    for _ in range(count):
        job = ScanJob(asset_id=asset.id, status="PENDING")
        session.add(job)
        session.flush()
        ids.append(job.id)
    session.commit()
    session.close()
    return ids


def test_concurrent_claims_never_double_claim(sqlite_file):
    """8 threads x 4 jobs: every job claimed at most once, total == 4."""
    job_ids = _insert_asset_and_jobs(sqlite_file, 4)
    claimed: list[int] = []
    claimed_lock = threading.Lock()
    barrier = threading.Barrier(9)

    def consumer():
        session = _make_session(sqlite_file)
        try:
            barrier.wait(timeout=15)
            while True:
                job = worker_queue.claim_next_pending_job(session)
                if job is None:
                    break
                with claimed_lock:
                    claimed.append(job.id)
                # Hold the RUNNING state briefly so other threads race
                time.sleep(0.01)
                worker_queue.mark_job_completed(
                    session, job.id, findings={"ports": []}, resolved_ip="127.0.0.1"
                )
        finally:
            session.close()

    threads = [threading.Thread(target=consumer) for _ in range(8)]
    for t in threads:
        t.start()
    barrier.wait(timeout=15)  # release all workers simultaneously
    for t in threads:
        t.join(timeout=60)

    assert sorted(claimed) == sorted(job_ids), (
        f"Expected each job claimed exactly once, got {sorted(claimed)}"
    )
    assert len(claimed) == len(set(claimed)) == 4

    session = _make_session(sqlite_file)
    statuses = [j.status for j in session.query(ScanJob).all()]
    session.close()
    assert all(s == "COMPLETED" for s in statuses)


def test_single_claim_per_job_under_contention(sqlite_file):
    """Two threads racing on one job: exactly one wins."""
    job_ids = _insert_asset_and_jobs(sqlite_file, 1)
    results: list[int | None] = []
    results_lock = threading.Lock()
    barrier = threading.Barrier(3)

    def consumer():
        session = _make_session(sqlite_file)
        try:
            barrier.wait(timeout=15)
            job = worker_queue.claim_next_pending_job(session)
            with results_lock:
                results.append(job.id if job else None)
        finally:
            session.close()

    t1 = threading.Thread(target=consumer)
    t2 = threading.Thread(target=consumer)
    t1.start(); t2.start()
    barrier.wait(timeout=15)
    t1.join(timeout=60); t2.join(timeout=60)

    winners = [r for r in results if r is not None]
    assert winners == [job_ids[0]]
    assert results.count(None) == 1


def test_attempts_incremented_on_claim(sqlite_file):
    """Each claim increments attempts so retry accounting stays correct."""
    job_ids = _insert_asset_and_jobs(sqlite_file, 1)
    session = _make_session(sqlite_file)
    job = worker_queue.claim_next_pending_job(session)
    assert job is not None and job.attempts == 1
    session.close()


def test_mark_job_failed_records_error(sqlite_file):
    """Failed jobs are marked FAILED with sanitized error fields."""
    job_ids = _insert_asset_and_jobs(sqlite_file, 1)
    session = _make_session(sqlite_file)
    job = worker_queue.claim_next_pending_job(session)
    assert job is not None
    worker_queue.mark_job_failed(
        session, job.id, error_code="NMAP_ERROR", error_message="nmap exited 1"
    )
    session.expire_all()
    job = session.get(ScanJob, job_ids[0])
    assert job.status == "FAILED"
    assert job.error_code == "NMAP_ERROR"
    assert job.finished_at is not None
    session.close()


def test_claim_returns_none_when_queue_empty(sqlite_file):
    """No pending jobs -> claim returns None (SCAN_ENABLED gate lives in the
    worker main loop, not in the queue layer)."""
    session = _make_session(sqlite_file)
    assert worker_queue.claim_next_pending_job(session) is None
    session.close()
