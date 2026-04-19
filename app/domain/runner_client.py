import http.client
import json
import os
import socket
from datetime import UTC, datetime

import requests
from requests import HTTPError, Response

from app.models.host_models import HostRecord


class UnixHttpConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str):
        super().__init__("localhost")
        self.socket_path = socket_path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)


def current_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_host_token(host_record: HostRecord) -> str:
    if not host_record.token_env_var:
        return ""
    return str(os.getenv(host_record.token_env_var) or "").strip()


def build_runner_headers(host_record: HostRecord) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    host_token = read_host_token(host_record)
    if host_token:
        headers["Authorization"] = f"Bearer {host_token}"
    return headers


def raise_for_runner_status(response_status: int, response_body: str, request_url: str) -> None:
    if 200 <= response_status < 300:
        return

    response = Response()
    response.status_code = response_status
    response.url = request_url
    response._content = response_body.encode("utf-8")
    raise HTTPError(f"{response_status} Server Error: runner request failed for url: {request_url}", response=response)


def build_default_runner_health(host_record: HostRecord, status: str, detail: str) -> dict:
    if host_record.transport == "socket":
        endpoint = host_record.runner_socket_path
    elif host_record.transport == "http":
        endpoint = host_record.runner_url
    else:
        endpoint = ""

    return {
        "status": status,
        "ok": status == "healthy",
        "checked_at": current_timestamp(),
        "detail": detail,
        "endpoint": endpoint,
        "transport": host_record.transport,
    }


def post_runner_request(host_record: HostRecord, path: str, payload: dict, timeout_seconds: int = 15) -> dict:
    headers = build_runner_headers(host_record)

    if host_record.transport == "socket":
        connection = UnixHttpConnection(host_record.runner_socket_path)
        connection.timeout = timeout_seconds
        connection.request("POST", path, body=json.dumps(payload), headers=headers)
        response = connection.getresponse()
        response_body = response.read().decode("utf-8")
        request_url = f"http+unix://{host_record.runner_socket_path}{path}"
        raise_for_runner_status(response.status, response_body, request_url)
        if not response_body.strip():
            return {}
        return json.loads(response_body)

    if host_record.transport == "http":
        response = requests.post(
            f"{host_record.runner_url.rstrip('/')}{path}",
            json=payload,
            headers=headers,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        if not response.text.strip():
            return {}
        return response.json()

    raise ValueError("Runner requests require an http or socket host.")


def get_runner_health(host_record: HostRecord, timeout_seconds: int = 10) -> dict:
    if host_record.transport == "none":
        return build_default_runner_health(host_record, "unconfigured", "No runner configured.")

    headers = build_runner_headers(host_record)

    try:
        if host_record.transport == "socket":
            connection = UnixHttpConnection(host_record.runner_socket_path)
            connection.timeout = timeout_seconds
            connection.request("GET", "/health", headers=headers)
            response = connection.getresponse()
            response_body = response.read().decode("utf-8")
            request_url = f"http+unix://{host_record.runner_socket_path}/health"
            raise_for_runner_status(response.status, response_body, request_url)
            response_payload = json.loads(response_body) if response_body.strip() else {}
        elif host_record.transport == "http":
            response = requests.get(
                f"{host_record.runner_url.rstrip('/')}/health",
                headers=headers,
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            response_payload = response.json() if response.text.strip() else {}
        else:
            raise ValueError("Runner health checks require an http or socket host.")
    except Exception as error:
        return build_default_runner_health(host_record, "down", f"Runner check failed: {error}")

    return {
        "status": "healthy" if bool(response_payload.get("ok", True)) else "down",
        "ok": bool(response_payload.get("ok", True)),
        "checked_at": str(response_payload.get("checked_at") or current_timestamp()),
        "detail": str(response_payload.get("detail") or "Runner reachable."),
        "endpoint": host_record.runner_socket_path if host_record.transport == "socket" else host_record.runner_url,
        "transport": host_record.transport,
    }
