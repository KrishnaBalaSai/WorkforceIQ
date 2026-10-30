"""
WorkforceIQ Backend – Database Connection Layer (Phase 5).

Provides:
  - SQLAlchemy engine with PostgreSQL (production).
  - CSV-backed in-memory store (development fallback when DB_URL is absent).
  - Session factory for dependency injection.
  - Health check utility.
"""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Generator, Optional

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger("workforceiq.database")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables

load_dotenv(PROJECT_ROOT / ".env")
# ---------------------------------------------------------------------------
# Configuration (read from environment – no hardcoded credentials)
# ---------------------------------------------------------------------------

def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(key, default)


DB_URL: Optional[str] = _env("DB_URL")  # None triggers CSV fallback
DB_POOL_SIZE: int = int(_env("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW: int = int(_env("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT: int = int(_env("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE: int = int(_env("DB_POOL_RECYCLE", "1800"))

DATA_GENERATED_DIR = PROJECT_ROOT / _env("DATA_GENERATED_DIR", "data/generated")
DATA_GROUND_TRUTH_DIR = PROJECT_ROOT / _env("DATA_GROUND_TRUTH_DIR", "data/ground_truth")
DATA_MANIFESTS_DIR = PROJECT_ROOT / _env("DATA_MANIFESTS_DIR", "data/manifests")

# ---------------------------------------------------------------------------
# SQLAlchemy Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Engine & SessionFactory (PostgreSQL)
# ---------------------------------------------------------------------------

_engine = None
_SessionLocal = None

def _build_engine():
    """Create a pooled SQLAlchemy engine from DB_URL."""
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    if not DB_URL:
        raise RuntimeError(
            "DB_URL environment variable is not set. "
            "Set DB_URL=postgresql+psycopg2://user:pass@host:5432/dbname "
            "or rely on the CSV fallback layer for development."
        )

    _engine = create_engine(
        DB_URL,
        poolclass=QueuePool,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_timeout=DB_POOL_TIMEOUT,
        pool_recycle=DB_POOL_RECYCLE,
        pool_pre_ping=True,          # validates connections before use
        echo=False,
    )

    # Log pool checkouts in debug mode
    @event.listens_for(_engine, "connect")
    def on_connect(dbapi_connection, connection_record):
        logger.debug("New database connection established.")

    _SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engine,
    )
    logger.info("PostgreSQL engine initialised (pool_size=%d).", DB_POOL_SIZE)
    return _engine


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session with automatic cleanup."""
    if not DB_URL:
        raise RuntimeError("Database not configured. DB_URL is missing.")
    if _SessionLocal is None:
        _build_engine()
    session: Session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

def check_database_health() -> dict:
    """
    Returns a health status dict. Tries PostgreSQL first, then reports
    CSV-fallback availability.
    """
    result = {
        "database_type": "postgresql" if DB_URL else "csv_fallback",
        "db_url_configured": bool(DB_URL),
        "postgresql_reachable": False,
        "csv_fallback_available": False,
        "csv_files_found": 0,
    }

    if DB_URL:
        try:
            eng = _build_engine()
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            result["postgresql_reachable"] = True
        except Exception:
            logger.exception("PostgreSQL health check failed.")
            result["postgresql_error"] = "Database connection unavailable."

    # Always report CSV fallback state
    csv_count = len(list(DATA_GENERATED_DIR.glob("*.csv"))) if DATA_GENERATED_DIR.exists() else 0
    result["csv_fallback_available"] = csv_count > 0
    result["csv_files_found"] = csv_count

    return result


# ---------------------------------------------------------------------------
# CSV Data Store (development fallback)
# ---------------------------------------------------------------------------

class CSVDataStore:
    """
    Singleton that loads all exported CSV datasets into pandas DataFrames.
    Used when PostgreSQL is not available. All reads are in-memory after init.
    """

    _instance: Optional["CSVDataStore"] = None

    def __init__(self):
        self._tables: dict[str, pd.DataFrame] = {}
        self._ground_truth: dict[str, pd.DataFrame] = {}
        self._load()

    def _load(self):
        if not DATA_GENERATED_DIR.exists():
            raise FileNotFoundError(
                f"Generated data directory not found: {DATA_GENERATED_DIR}. "
                "Run the data generator first."
            )
        for csv_path in sorted(DATA_GENERATED_DIR.glob("*.csv")):
            tbl = csv_path.stem
            self._tables[tbl] = pd.read_csv(csv_path, low_memory=False)
            logger.debug("Loaded %s: %d rows", tbl, len(self._tables[tbl]))

        for csv_path in sorted(DATA_GROUND_TRUTH_DIR.glob("*.csv")):
            tbl = csv_path.stem
            self._ground_truth[tbl] = pd.read_csv(csv_path, low_memory=False)

        logger.info(
            "CSVDataStore loaded: %d tables, %d ground_truth tables.",
            len(self._tables),
            len(self._ground_truth),
        )

    def table(self, name: str) -> pd.DataFrame:
        if name not in self._tables:
            raise KeyError(f"Table '{name}' not found in CSV store.")
        return self._tables[name].copy()

    def ground_truth(self, name: str) -> pd.DataFrame:
        if name not in self._ground_truth:
            raise KeyError(f"Ground-truth table '{name}' not found.")
        return self._ground_truth[name].copy()

    @classmethod
    def get(cls) -> "CSVDataStore":
        if cls._instance is None:
            cls._instance = CSVDataStore()
        return cls._instance

    @classmethod
    def reset(cls):
        """Clears the singleton — used in tests."""
        cls._instance = None


@lru_cache(maxsize=1)
def get_csv_store() -> CSVDataStore:
    """Cached accessor for the CSV data store."""
    return CSVDataStore.get()
