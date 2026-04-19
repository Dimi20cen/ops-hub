from fastapi import APIRouter, HTTPException

from app.domain.action_service import run_project_action
from app.domain.health_service import run_project_health_check
from app.domain.project_service import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    save_project_health_snapshot,
    update_project,
)
from app.models.project_models import ProjectActionRequest, ProjectUpsertRequest


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def get_projects() -> dict:
    return {"projects": [project.model_dump() for project in list_projects()]}


@router.post("")
async def post_project(project_request: ProjectUpsertRequest) -> dict:
    try:
        project_record = create_project(project_request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"project": project_record.model_dump()}


@router.put("/{project_slug}")
async def put_project(project_slug: str, project_request: ProjectUpsertRequest) -> dict:
    if get_project(project_slug) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        project_record = update_project(project_slug, project_request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"project": project_record.model_dump()}


@router.delete("/{project_slug}")
async def remove_project(project_slug: str) -> dict:
    if get_project(project_slug) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        removed_project_record = delete_project(project_slug)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"project": removed_project_record.model_dump()}


@router.post("/{project_slug}/health-check")
async def post_project_health_check(project_slug: str) -> dict:
    project_record = get_project(project_slug)
    if project_record is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    health_snapshot = run_project_health_check(project_record)
    save_project_health_snapshot(project_slug, health_snapshot)
    return health_snapshot


@router.post("/{project_slug}/actions")
async def post_project_action(project_slug: str, action_request: ProjectActionRequest) -> dict:
    project_record = get_project(project_slug)
    if project_record is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        return run_project_action(project_record, action_request.action, dry_run=action_request.dry_run)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
