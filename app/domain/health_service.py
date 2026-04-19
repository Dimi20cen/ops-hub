from datetime import UTC, datetime

import requests

from app.domain.host_service import get_host
from app.domain.runner_client import post_runner_request
from app.models.project_models import ProjectRecord


def current_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_unconfigured_check(check_label: str) -> dict:
    return {
        "label": check_label,
        "status": "unconfigured",
        "ok": False,
        "http_status": None,
        "detail": "No URL configured.",
        "checked_at": current_timestamp(),
        "url": "",
    }


def run_direct_health_check(check_label: str, health_url: str) -> dict:
    if not health_url:
        return build_unconfigured_check(check_label)
    try:
        response = requests.get(health_url, timeout=5)
        return {
            "label": check_label,
            "status": "healthy" if 200 <= response.status_code < 400 else "down",
            "ok": 200 <= response.status_code < 400,
            "http_status": response.status_code,
            "detail": f"HTTP {response.status_code}",
            "checked_at": current_timestamp(),
            "url": health_url,
        }
    except requests.RequestException as error:
        return {
            "label": check_label,
            "status": "down",
            "ok": False,
            "http_status": None,
            "detail": str(error),
            "checked_at": current_timestamp(),
            "url": health_url,
        }


def run_health_check_via_host_runner(check_label: str, health_url: str, deployment_host_slug: str) -> dict:
    if not health_url:
        return build_unconfigured_check(check_label)

    host_record = get_host(deployment_host_slug)
    if host_record is None or host_record.transport == "none":
        return run_direct_health_check(check_label, health_url)

    try:
        runner_response = post_runner_request(
            host_record=host_record,
            path="/check-url",
            payload={"label": check_label, "url": health_url, "timeout_seconds": 5},
            timeout_seconds=10,
        )
    except Exception as error:
        return {
            "label": check_label,
            "status": "down",
            "ok": False,
            "http_status": None,
            "detail": f"Runner check failed: {error}",
            "checked_at": current_timestamp(),
            "url": health_url,
        }

    return {
        "label": check_label,
        "status": str(runner_response.get("status") or "unknown"),
        "ok": bool(runner_response.get("ok")),
        "http_status": runner_response.get("http_status"),
        "detail": str(runner_response.get("detail") or ""),
        "checked_at": str(runner_response.get("checked_at") or current_timestamp()),
        "url": health_url,
    }


def summarize_project_health(public_check: dict, private_check: dict) -> str:
    if public_check["ok"] and private_check["ok"]:
        return "healthy"
    if public_check["status"] == "unconfigured" and private_check["status"] == "unconfigured":
        return "unconfigured"
    if public_check["ok"] or private_check["ok"]:
        return "partial"
    return "down"


def run_project_health_check(project_record: ProjectRecord) -> dict:
    public_check = run_direct_health_check("public", project_record.health_public_url)
    private_check = run_health_check_via_host_runner(
        "private",
        project_record.health_private_url,
        project_record.deployment_host,
    )
    return {
        "project_slug": project_record.slug,
        "summary": summarize_project_health(public_check, private_check),
        "checks": {
            "public": public_check,
            "private": private_check,
        },
        "checked_at": current_timestamp(),
    }
