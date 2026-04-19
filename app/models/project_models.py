from typing import Literal

from pydantic import BaseModel, Field, field_validator


ProjectActionName = Literal["deploy", "start", "restart", "stop", "logs"]
ProjectVisibility = Literal["private", "internal", "public"]
ProjectSurface = Literal["source", "private_deploy", "public_demo", "public_deploy"]


class ProjectRecord(BaseModel):
    slug: str
    title: str
    description: str = ""
    visibility: ProjectVisibility = "private"
    project_surfaces: list[ProjectSurface] = Field(default_factory=list)
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

    @field_validator("project_surfaces")
    @classmethod
    def normalize_project_surfaces(cls, project_surfaces: list[ProjectSurface]) -> list[ProjectSurface]:
        unique_project_surfaces: list[ProjectSurface] = []
        for project_surface in project_surfaces:
            if project_surface in unique_project_surfaces:
                continue
            unique_project_surfaces.append(project_surface)
        return unique_project_surfaces


class ProjectUpsertRequest(BaseModel):
    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    visibility: ProjectVisibility = "private"
    project_surfaces: list[ProjectSurface] = Field(default_factory=list)
    deployment_host: str = ""
    runtime_path: str = ""
    health_public_url: str = ""
    health_private_url: str = ""
    deploy_command: str = ""
    start_command: str = ""
    restart_command: str = ""
    stop_command: str = ""
    logs_command: str = ""

    @field_validator("project_surfaces", mode="before")
    @classmethod
    def normalize_project_surface_inputs(cls, project_surfaces: object) -> list[str]:
        if project_surfaces is None:
            return []
        if not isinstance(project_surfaces, list):
            raise ValueError("project_surfaces must be a list.")

        normalized_project_surfaces: list[str] = []
        for project_surface in project_surfaces:
            if not isinstance(project_surface, str):
                raise ValueError("project_surfaces must only contain strings.")

            cleaned_project_surface = project_surface.strip().lower()
            if not cleaned_project_surface:
                continue
            if cleaned_project_surface in normalized_project_surfaces:
                continue
            normalized_project_surfaces.append(cleaned_project_surface)

        return normalized_project_surfaces


class ProjectActionRequest(BaseModel):
    action: ProjectActionName
    dry_run: bool = False
