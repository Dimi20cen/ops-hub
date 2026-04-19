import asyncio
import logging
import os

from app.domain.health_service import run_project_health_check
from app.domain.project_service import list_projects, save_project_health_snapshot


logger = logging.getLogger(__name__)
DEFAULT_AUTO_HEALTH_CHECK_INTERVAL_SECONDS = 300
MINIMUM_AUTO_HEALTH_CHECK_INTERVAL_SECONDS = 30


def is_auto_health_check_enabled() -> bool:
    configured_value = str(os.getenv("OPS_HUB_AUTO_HEALTH_CHECK_ENABLED", "true")).strip().lower()
    return configured_value not in {"0", "false", "no", "off"}


def get_auto_health_check_interval_seconds() -> int:
    configured_value = str(
        os.getenv(
            "OPS_HUB_AUTO_HEALTH_CHECK_INTERVAL_SECONDS",
            str(DEFAULT_AUTO_HEALTH_CHECK_INTERVAL_SECONDS),
        )
    ).strip()
    try:
        configured_interval_seconds = int(configured_value)
    except ValueError:
        logger.warning(
            "Invalid OPS_HUB_AUTO_HEALTH_CHECK_INTERVAL_SECONDS=%r. Falling back to %s seconds.",
            configured_value,
            DEFAULT_AUTO_HEALTH_CHECK_INTERVAL_SECONDS,
        )
        return DEFAULT_AUTO_HEALTH_CHECK_INTERVAL_SECONDS
    return max(MINIMUM_AUTO_HEALTH_CHECK_INTERVAL_SECONDS, configured_interval_seconds)


def run_auto_health_check_sweep() -> None:
    for project_record in list_projects():
        try:
            health_snapshot = run_project_health_check(project_record)
            save_project_health_snapshot(project_record.slug, health_snapshot)
        except Exception:
            logger.exception(
                "Automatic health check failed for project '%s'.",
                project_record.slug,
            )


async def run_auto_health_check_loop(stop_event: asyncio.Event) -> None:
    interval_seconds = get_auto_health_check_interval_seconds()
    logger.info(
        "Automatic health checks enabled with %s second interval.",
        interval_seconds,
    )

    while not stop_event.is_set():
        await asyncio.to_thread(run_auto_health_check_sweep)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue
