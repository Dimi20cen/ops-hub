from typing import Literal

from pydantic import BaseModel, Field


ProjectActionName = Literal["deploy", "start", "restart", "stop", "logs"]
ProjectVisibility = Literal["private", "internal", "public"]


class ProjectRecord(BaseModel):
    slug: str
    title: str
    description: str = ""
    visibility: ProjectVisibility = "private"
    deployment_host: str = ""
    runtime_path: str = ""
    health_public_url: str = ""
    health_private_url: str = ""
    deploy_command: str = ""
    start_command: str = ""
    restart_command: str = ""
    stop_command: str = ""
    logs_command: str = ""
    last_health_summary: str = "not_checked"
    last_health_checked_at: str = ""
    last_health_result: dict = Field(default_factory=dict)
    updated_at: str = ""


class ProjectUpsertRequest(BaseModel):
    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    visibility: ProjectVisibility = "private"
    deployment_host: str = ""
    runtime_path: str = ""
    health_public_url: str = ""
    health_private_url: str = ""
    deploy_command: str = ""
    start_command: str = ""
    restart_command: str = ""
    stop_command: str = ""
    logs_command: str = ""


class ProjectActionRequest(BaseModel):
    action: ProjectActionName
    dry_run: bool = False
