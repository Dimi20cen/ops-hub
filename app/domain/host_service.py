from datetime import UTC, datetime
from urllib.parse import urlparse

from app.models.host_models import HostRecord, HostUpsertRequest, HostViewRecord
from app.domain.runner_client import get_runner_health
from app.storage.json_store import get_hosts_path, load_store_data, write_store_data


def current_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_slug(value: str) -> str:
    safe_value = "".join(character.lower() if character.isalnum() else "-" for character in value.strip())
    return "-".join(part for part in safe_value.split("-") if part)


def validate_optional_http_url(field_name: str, value: str) -> str:
    cleaned_value = value.strip()
    if not cleaned_value:
        return ""
    parsed_url = urlparse(cleaned_value)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError(f"{field_name} must be a full http/https URL.")
    return cleaned_value


def normalize_host_record(host_request: HostUpsertRequest, existing_updated_at: str = "") -> HostRecord:
    host_slug = normalize_slug(host_request.slug)
    host_title = host_request.title.strip()
    host_transport = host_request.transport
    runner_url = validate_optional_http_url("runner_url", host_request.runner_url)
    runner_socket_path = host_request.runner_socket_path.strip()
    token_env_var = host_request.token_env_var.strip()

    if not host_slug:
        raise ValueError("Host slug is required.")
    if not host_title:
        raise ValueError("Host title is required.")
    if host_transport == "http" and not runner_url:
        raise ValueError("HTTP hosts require a runner_url.")
    if host_transport == "http" and not token_env_var:
        raise ValueError("HTTP hosts require a token_env_var.")
    if host_transport == "socket" and not runner_socket_path:
        raise ValueError("Socket hosts require a runner_socket_path.")

    if host_transport != "http":
        runner_url = ""
    if host_transport != "socket":
        runner_socket_path = ""

    return HostRecord(
        slug=host_slug,
        title=host_title,
        transport=host_transport,
        runner_url=runner_url,
        runner_socket_path=runner_socket_path,
        token_env_var=token_env_var,
        location=host_request.location.strip(),
        notes=host_request.notes.strip(),
        updated_at=existing_updated_at or current_timestamp(),
    )


def list_hosts() -> list[HostRecord]:
    host_payloads = load_store_data(get_hosts_path())
    host_records = [HostRecord.model_validate(host_payload) for host_payload in host_payloads]
    return sorted(host_records, key=lambda host_record: (host_record.title.lower(), host_record.slug))


def list_host_views() -> list[HostViewRecord]:
    host_views: list[HostViewRecord] = []
    for host_record in list_hosts():
        host_views.append(
            HostViewRecord(
                **host_record.model_dump(),
                runner_health=get_runner_health(host_record),
            )
        )
    return host_views


def get_host(host_slug: str) -> HostRecord | None:
    normalized_host_slug = normalize_slug(host_slug)
    for host_record in list_hosts():
        if host_record.slug == normalized_host_slug:
            return host_record
    return None


def create_host(host_request: HostUpsertRequest) -> HostRecord:
    existing_hosts = list_hosts()
    new_host_record = normalize_host_record(host_request)
    if any(existing_host.slug == new_host_record.slug for existing_host in existing_hosts):
        raise ValueError("Host slug already exists.")
    updated_hosts = [*existing_hosts, new_host_record]
    write_store_data(get_hosts_path(), [host.model_dump() for host in updated_hosts])
    return new_host_record


def update_host(host_slug: str, host_request: HostUpsertRequest) -> HostRecord:
    normalized_host_slug = normalize_slug(host_slug)
    existing_hosts = list_hosts()
    updated_hosts: list[HostRecord] = []
    replacement_host_record: HostRecord | None = None

    for existing_host in existing_hosts:
        if existing_host.slug != normalized_host_slug:
            updated_hosts.append(existing_host)
            continue
        if normalize_slug(host_request.slug) != normalized_host_slug:
            raise ValueError("Host slug cannot be changed.")
        replacement_host_record = normalize_host_record(host_request, existing_updated_at=current_timestamp())
        updated_hosts.append(replacement_host_record)

    if replacement_host_record is None:
        raise ValueError("Host not found.")

    write_store_data(get_hosts_path(), [host.model_dump() for host in updated_hosts])
    return replacement_host_record


def delete_host(host_slug: str) -> HostRecord:
    from app.domain.project_service import list_projects

    normalized_host_slug = normalize_slug(host_slug)
    dependent_projects = [
        project.slug for project in list_projects() if project.deployment_host == normalized_host_slug
    ]
    if dependent_projects:
        joined_project_slugs = ", ".join(sorted(dependent_projects))
        raise ValueError(f"Cannot delete host while projects still reference it: {joined_project_slugs}.")

    existing_hosts = list_hosts()
    remaining_hosts: list[HostRecord] = []
    removed_host_record: HostRecord | None = None

    for existing_host in existing_hosts:
        if existing_host.slug == normalized_host_slug:
            removed_host_record = existing_host
            continue
        remaining_hosts.append(existing_host)

    if removed_host_record is None:
        raise ValueError("Host not found.")

    write_store_data(get_hosts_path(), [host.model_dump() for host in remaining_hosts])
    return removed_host_record
