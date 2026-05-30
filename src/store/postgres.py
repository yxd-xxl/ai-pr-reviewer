"""PostgreSQL-backed storage — SQLAlchemy ORM, Alembic migrations, same interface as SQLite."""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

try:
    from sqlalchemy import (
        create_engine, Column, Integer, String, Float, Boolean, Text,
        ForeignKey, DateTime, MetaData, Table,
    )
    from sqlalchemy.orm import sessionmaker, declarative_base, Session
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

Base = declarative_base() if HAS_SQLALCHEMY else None


def _now():
    return datetime.now(timezone.utc)


# ── ORM Models ──────────────────────────────────

if HAS_SQLALCHEMY:
    class ReviewRun(Base):
        __tablename__ = "review_runs"
        id = Column(Integer, primary_key=True, autoincrement=True)
        pr_url = Column(String, nullable=False)
        pr_title = Column(String)
        repo = Column(String, index=True)
        pr_author = Column(String)
        base_sha = Column(String)
        head_sha = Column(String)
        files_count = Column(Integer, default=0)
        lines_added = Column(Integer, default=0)
        lines_deleted = Column(Integer, default=0)
        findings_count = Column(Integer, default=0)
        risk_score = Column(Integer, default=0)
        mode = Column(String, default="balanced")
        categories = Column(String, default="all")
        llm_provider = Column(String)
        llm_model = Column(String)
        prompt_version = Column(String)
        created_at = Column(DateTime, default=_now)

    class Finding(Base):
        __tablename__ = "findings"
        id = Column(Integer, primary_key=True, autoincrement=True)
        review_run_id = Column(Integer, ForeignKey("review_runs.id"), nullable=False)
        severity = Column(String)
        category = Column(String)
        classification = Column(String, default="new")
        title = Column(String)
        file = Column(String)
        line = Column(Integer)
        confidence = Column(Float)
        evidence = Column(Text)
        suggestion = Column(Text)
        fix_patch = Column(Text)
        fingerprint = Column(String, index=True)
        lifecycle_state = Column(String, default="detected")

    class FeedbackEvent(Base):
        __tablename__ = "feedback_events"
        id = Column(Integer, primary_key=True, autoincrement=True)
        fingerprint = Column(String, index=True, nullable=False)
        state = Column(String, default="unmarked")
        user = Column(String, default="unknown")
        reason = Column(Text, default="")
        created_at = Column(DateTime, default=_now)


class PostgresReviewRepo:
    """PostgreSQL-backed review repository — same interface as SQLite ReviewRepo."""

    def __init__(self, database_url: str | None = None):
        if not HAS_SQLALCHEMY:
            raise RuntimeError("SQLAlchemy required for PostgreSQL. pip install sqlalchemy psycopg2-binary")

        self._url = database_url or os.getenv("DATABASE_URL", "postgresql://localhost:5432/ai_pr_reviewer")
        self._engine = create_engine(self._url, pool_size=5, max_overflow=10)
        Base.metadata.create_all(self._engine)
        self._Session = sessionmaker(bind=self._engine)

    def save_review(self, pr_url: str, pr_title: str, repo: str,
                    findings: list, risk_score: int = 0,
                    mode: str = "balanced", categories: str = "all") -> int:
        with self._Session() as session:
            run = ReviewRun(
                pr_url=pr_url, pr_title=pr_title, repo=repo,
                findings_count=len(findings), risk_score=risk_score,
                mode=mode, categories=categories,
                created_at=_now(),
            )
            session.add(run)
            session.flush()

            for f in findings:
                fp = _make_fingerprint(f)
                session.add(Finding(
                    review_run_id=run.id,
                    severity=f.severity, category=f.category,
                    title=f.title, file=f.location.file,
                    line=f.location.line, confidence=f.confidence,
                    evidence=f.evidence, suggestion=f.suggestion,
                    fix_patch=f.fix_patch, fingerprint=fp,
                ))

            session.commit()
            return run.id

    def get_history(self, repo: str = "", limit: int = 20) -> list[dict]:
        with self._Session() as session:
            q = session.query(ReviewRun)
            if repo:
                q = q.filter(ReviewRun.repo == repo)
            rows = q.order_by(ReviewRun.created_at.desc()).limit(limit).all()
            return [_row_to_dict(r) for r in rows]

    def get_findings(self, run_id: int) -> list[dict]:
        with self._Session() as session:
            rows = session.query(Finding).filter(
                Finding.review_run_id == run_id
            ).order_by(Finding.severity, Finding.confidence.desc()).all()
            return [_row_to_dict(r) for r in rows]

    def mark_feedback(self, fingerprint: str, state: str,
                      user: str = "unknown", reason: str = ""):
        with self._Session() as session:
            session.add(FeedbackEvent(
                fingerprint=fingerprint, state=state, user=user,
                reason=reason, created_at=_now(),
            ))
            session.commit()

    def close(self):
        self._engine.dispose()


def _row_to_dict(row) -> dict:
    """Convert SQLAlchemy model instance to dict."""
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def _make_fingerprint(finding) -> str:
    import hashlib
    key = f"{finding.location.file}:{finding.location.line}:{finding.title}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def create_review_repo(database_url: str | None = None):
    """Factory: return PostgresReviewRepo if DATABASE_URL set, else SQLite ReviewRepo."""
    if database_url or os.getenv("DATABASE_URL"):
        return PostgresReviewRepo(database_url)
    from src.store.db import ReviewRepo
    return ReviewRepo()
