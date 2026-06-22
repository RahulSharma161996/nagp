import os
import threading
import time
from typing import List, Optional

import psycopg
from psycopg_pool import ConnectionPool
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class Record(BaseModel):
    id: int
    name: str
    value: int


def _env(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def _conninfo() -> str:
    return (
        f"host={_env('DB_HOST')} port={_env('DB_PORT', '5432')} "
        f"dbname={_env('DB_NAME')} user={_env('DB_USER')} password={_env('DB_PASSWORD')}"
    )


app = FastAPI(title="NAGP 2026 API")

_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def _init_pool() -> ConnectionPool:
    # Keep the app process alive even if DB isn't ready yet.
    # Kubernetes readiness will gate traffic until the DB connection succeeds.
    last_err: Optional[Exception] = None
    for _ in range(30):  # ~60s worst case
        try:
            return ConnectionPool(conninfo=_conninfo(), min_size=1, max_size=10, open=True)
        except Exception as e:
            last_err = e
            time.sleep(2)
    raise RuntimeError(f"Failed to initialize DB pool: {last_err}") from last_err


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _pool is None:
            _pool = _init_pool()
    return _pool


@app.get("/healthz")
def healthz():
    try:
        pool = _get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "not_ready", "error": str(e)})


@app.get("/records", response_model=List[Record])
def records():
    pool = _get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, value FROM records ORDER BY id;")
            rows = cur.fetchall()
    return [Record(id=r[0], name=r[1], value=r[2]) for r in rows]