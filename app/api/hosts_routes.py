from fastapi import APIRouter, HTTPException

from app.domain.host_service import create_host, delete_host, get_host, list_host_views, update_host
from app.models.host_models import HostUpsertRequest


router = APIRouter(prefix="/hosts", tags=["hosts"])


@router.get("")
async def get_hosts() -> dict:
    return {"hosts": [host.model_dump() for host in list_host_views()]}


@router.post("")
async def post_host(host_request: HostUpsertRequest) -> dict:
    try:
        host_record = create_host(host_request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"host": host_record.model_dump()}


@router.put("/{host_slug}")
async def put_host(host_slug: str, host_request: HostUpsertRequest) -> dict:
    if get_host(host_slug) is None:
        raise HTTPException(status_code=404, detail="Host not found.")
    try:
        host_record = update_host(host_slug, host_request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"host": host_record.model_dump()}


@router.delete("/{host_slug}")
async def remove_host(host_slug: str) -> dict:
    if get_host(host_slug) is None:
        raise HTTPException(status_code=404, detail="Host not found.")
    try:
        removed_host_record = delete_host(host_slug)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"host": removed_host_record.model_dump()}
