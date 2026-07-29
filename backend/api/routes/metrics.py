import time
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from core.config.settings import settings
from core.database.app_session import AppSessionLocal

router = APIRouter(tags=["monitoring"])


@router.get("/metrics", response_class=Response)
async def prometheus_metrics():
    """
    Exposes Prometheus-formatted operational metrics for observability, SLAs, and monitoring alerts.
    """
    lines = [
        "# HELP asila_up System availability indicator (1 = healthy, 0 = degraded)",
        "# TYPE asila_up gauge",
    ]
    
    # Check Database Health
    db_ok = 1
    db_latency_ms = 0.0
    try:
        t0 = time.perf_counter()
        async with AppSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_latency_ms = (time.perf_counter() - t0) * 1000.0
    except Exception:
        db_ok = 0

    system_up = 1 if db_ok == 1 else 0

    lines.extend([
        f"asila_up {system_up}",
        "# HELP asila_database_status PostgreSQL database availability",
        "# TYPE asila_database_status gauge",
        f"asila_database_status {db_ok}",
        "# HELP asila_database_ping_latency_ms PostgreSQL ping latency in milliseconds",
        "# TYPE asila_database_ping_latency_ms gauge",
        f"asila_database_ping_latency_ms {round(db_latency_ms, 3)}",
    ])

    return Response(content="\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
