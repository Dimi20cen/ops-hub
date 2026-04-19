from datetime import UTC, datetime
from urllib.parse import urlparse

from app.domain.host_service import get_host, normalize_slug
from app.models.project_models import ProjectRecord, ProjectUpsertRequest
from app.storage.json_store import get_projects_path, load_store_data, write_store_data


def current_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_optional_http_url(field_name: str, value: str) -> str:
    cleaned_value = value.strip()
    if not cleaned_value:
        return ""
    parsed_url = urlparse(cleaned_value)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError(f"{field_name} must be a full http/https URL.")
    return cleaned_value


def normalize_project_record(
    project_request: ProjectUpsertRequest,
    existing_updated_at: str = "",
    existing_health_summary: str = "not_checked",
    existing_health_checked_at: str = "",
    existing_health_result: dict | None = None,
) -> ProjectRecord:
    project_slug = normalize_slug(project_request.slug)
    project_title = project_request.title.strip()
    deployment_host = normalize_slug(project_request.deployment_host) if project_request.deployment_host else ""

    if not project_slug:
        raise ValueError("Project slug is required.")
    if not project_title:
        raise ValueError("Project title is required.")
    if deployment_host and not get_host(deployment_host):
        raise ValueError(f"Unknown deployment_host '{deployment_host}'.")

    return ProjectRecord(
        slug=project_slug,
        title=project_title,
        description=project_request.description.strip(),
        visibility=project_request.visibility,
        project_surfaces=project_request.project_surfaces,
        deployment_host=deployment_host,
        runtime_path=project_request.runtime_path.strip(),
        health_public_url=validate_optional_http_url("health_public_url", project_request.health_public_url),
        health_private_url=validate_optional_http_url("health_private_url", project_request.health_private_url),
        deploy_command=project_request.deploy_command.strip(),
        start_command=project_request.start_command.strip(),
        restart_command=project_request.restart_command.strip(),
        stop_command=project_request.stop_command.strip(),
        logs_command=project_request.logs_command.strip(),
        last_health_summary=existing_health_summary or "not_checked",
        last_health_checked_at=existing_health_checked_at,
        last_health_result=existing_health_result or {},
        updated_at=existing_updated_at or current_timestamp(),
    )


def list_projects() -> list[ProjectRecord]:
    project_payloads = load_store_data(get_projects_path())
    project_records = [ProjectRecord.model_validate(project_payload) for project_payload in project_payloads]
    return sorted(project_records, key=lambda project_record: (project_record.title.lower(), project_record.slug))


def get_project(project_slug: str) -> ProjectRecord | None:
    normalized_project_slug = normalize_slug(project_slug)
    for project_record in list_projects():
        if project_record.slug == normalized_project_slug:
            return project_record
    return None


def create_project(project_request: ProjectUpsertRequest) -> ProjectRecord:
    existing_projects = list_projects()
    new_project_record = normalize_project_record(project_request)
    if any(existing_project.slug == new_project_record.slug for existing_project in existing_projects):
        raise ValueError("Project slug already exists.")
    updated_projects = [*existing_projects, new_project_record]
    write_store_data(get_projects_path(), [project.model_dump() for project in updated_projects])
    return new_project_record


def update_project(project_slug: str, project_request: ProjectUpsertRequest) -> ProjectRecord:
    normalized_project_slug = normalize_slug(project_slug)
    existing_projects = list_projects()
    updated_projects: list[ProjectRecord] = []
    replacement_project_record: ProjectRecord | None = None

    for existing_project in existing_projects:
        if existing_project.slug != normalized_project_slug:
            updated_projects.append(existing_project)
            continue
        if normalize_slug(project_request.slug) != normalized_project_slug:
            raise ValueError("Project slug cannot be changed.")
        replacement_project_record = normalize_project_record(
            project_request,
            existing_updated_at=current_timestamp(),
            existing_health_summary=existing_project.last_health_summary,
            existing_health_checked_at=existing_project.last_health_checked_at,
            existing_health_result=existing_project.last_health_result,
        )
        updated_projects.append(replacement_project_record)

    if replacement_project_record is None:
        raise ValueError("Project not found.")

    write_store_data(get_projects_path(), [project.model_dump() for project in updated_projects])
    return replacement_project_record


def delete_project(project_slug: str) -> ProjectRecord:
    normalized_project_slug = normalize_slug(project_slug)
    existing_projects = list_projects()
    remaining_projects: list[ProjectRecord] = []
    removed_project_record: ProjectRecord | None = None

    for existing_project in existing_projects:
        if existing_project.slug == normalized_project_slug:
            removed_project_record = existing_project
            continue
        remaining_projects.append(existing_project)

    if removed_project_record is None:
        raise ValueError("Project not found.")

    write_store_data(get_projects_path(), [project.model_dump() for project in remaining_projects])
    return removed_project_record


def save_project_health_snapshot(project_slug: str, health_snapshot: dict) -> ProjectRecord:
    normalized_project_slug = normalize_slug(project_slug)
    existing_projects = list_projects()
    updated_projects: list[ProjectRecord] = []
    cached_project_record: ProjectRecord | None = None

    for existing_project in existing_projects:
        if existing_project.slug != normalized_project_slug:
            updated_projects.append(existing_project)
            continue

        cached_project_record = existing_project.model_copy(
            update={
                "last_health_summary": str(health_snapshot.get("summary") or "not_checked"),
                "last_health_checked_at": str(health_snapshot.get("checked_at") or ""),
                "last_health_result": health_snapshot,
            }
        )
        updated_projects.append(cached_project_record)

    if cached_project_record is None:
        raise ValueError("Project not found.")

    write_store_data(get_projects_path(), [project.model_dump() for project in updated_projects])
    return cached_project_record
