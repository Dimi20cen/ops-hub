import subprocess
from datetime import UTC, datetime
from requests import HTTPError

from app.domain.host_service import get_host
from app.domain.runner_client import post_runner_request
from app.models.project_models import ProjectRecord


ACTION_TO_COMMAND_FIELD = {
    "deploy": "deploy_command",
    "start": "start_command",
    "restart": "restart_command",
    "stop": "stop_command",
    "logs": "logs_command",
}


def current_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_action_result(
    project_record: ProjectRecord,
    action_name: str,
    command_value: str,
    execution_mode: str,
    host_slug: str,
    dry_run: bool,
    ok: bool,
    exit_code: int | None,
    stdout: str,
    stderr: str,
) -> dict:
    return {
        "ok": ok,
        "action": action_name,
        "project_slug": project_record.slug,
        "host_slug": host_slug,
        "execution_mode": execution_mode,
        "dry_run": dry_run,
        "command": command_value,
        "cwd": project_record.runtime_path,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "ran_at": current_timestamp(),
    }


def run_project_action(project_record: ProjectRecord, action_name: str, dry_run: bool = False) -> dict:
    command_field_name = ACTION_TO_COMMAND_FIELD.get(action_name)
    if not command_field_name:
        raise ValueError(f"Unsupported action '{action_name}'.")

    command_value = str(getattr(project_record, command_field_name) or "").strip()
    if not command_value:
        raise ValueError(f"Project '{project_record.slug}' does not define a {action_name} command.")

    execution_mode = "local"
    host_slug = ""
    if project_record.deployment_host:
        host_record = get_host(project_record.deployment_host)
        if host_record is None:
            raise ValueError(f"Unknown deployment_host '{project_record.deployment_host}'.")
        host_slug = host_record.slug
        if host_record.transport in {"http", "socket"}:
            execution_mode = f"runner_{host_record.transport}"
            if dry_run:
                return build_action_result(
                    project_record=project_record,
                    action_name=action_name,
                    command_value=command_value,
                    execution_mode=execution_mode,
                    host_slug=host_slug,
                    dry_run=True,
                    ok=True,
                    exit_code=None,
                    stdout="",
                    stderr="",
                )
            return run_project_action_via_host_runner(
                project_record=project_record,
                action_name=action_name,
                command_value=command_value,
                execution_mode=execution_mode,
                host_slug=host_slug,
            )

    if not host_slug and project_record.deployment_host:
        host_slug = project_record.deployment_host

    if dry_run:
        return build_action_result(
            project_record=project_record,
            action_name=action_name,
            command_value=command_value,
            execution_mode=execution_mode,
            host_slug=host_slug,
            dry_run=True,
            ok=True,
            exit_code=None,
            stdout="",
            stderr="",
        )

    return run_project_action_locally(
        project_record=project_record,
        action_name=action_name,
        command_value=command_value,
        execution_mode=execution_mode,
        host_slug=host_slug,
    )


def run_project_action_locally(
    project_record: ProjectRecord,
    action_name: str,
    command_value: str,
    execution_mode: str,
    host_slug: str,
) -> dict:
    try:
        completed_process = subprocess.run(
            command_value,
            shell=True,
            cwd=project_record.runtime_path or None,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as error:
        return build_action_result(
            project_record=project_record,
            action_name=action_name,
            command_value=command_value,
            execution_mode=execution_mode,
            host_slug=host_slug,
            dry_run=False,
            ok=False,
            exit_code=None,
            stdout="",
            stderr=str(error),
        )

    return build_action_result(
        project_record=project_record,
        action_name=action_name,
        command_value=command_value,
        execution_mode=execution_mode,
        host_slug=host_slug,
        dry_run=False,
        ok=completed_process.returncode == 0,
        exit_code=completed_process.returncode,
        stdout=completed_process.stdout,
        stderr=completed_process.stderr,
    )


def run_project_action_via_host_runner(
    project_record: ProjectRecord,
    action_name: str,
    command_value: str,
    execution_mode: str,
    host_slug: str,
) -> dict:
    host_record = get_host(project_record.deployment_host)
    if host_record is None:
        raise ValueError(f"Unknown deployment_host '{project_record.deployment_host}'.")

    try:
        runner_response = post_runner_request(
            host_record=host_record,
            path="/run",
            payload={
                "action": action_name,
                "command": command_value,
                "cwd": project_record.runtime_path,
            },
            timeout_seconds=60,
        )
    except HTTPError as error:
        runner_error_body = ""
        if error.response is not None and error.response.text:
            runner_error_body = error.response.text
        return build_action_result(
            project_record=project_record,
            action_name=action_name,
            command_value=command_value,
            execution_mode=execution_mode,
            host_slug=host_slug,
            dry_run=False,
            ok=False,
            exit_code=None,
            stdout="",
            stderr=runner_error_body or str(error),
        )

    action_result = build_action_result(
        project_record=project_record,
        action_name=action_name,
        command_value=command_value,
        execution_mode=execution_mode,
        host_slug=host_slug,
        dry_run=False,
        ok=bool(runner_response.get("ok")),
        exit_code=runner_response.get("exit_code"),
        stdout=str(runner_response.get("stdout") or ""),
        stderr=str(runner_response.get("stderr") or ""),
    )
    action_result["ran_at"] = str(runner_response.get("ran_at") or current_timestamp())
    return action_result
