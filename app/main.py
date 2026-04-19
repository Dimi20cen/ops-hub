import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.hosts_routes import router as hosts_router
from app.api.projects_routes import router as projects_router
from app.domain.health_scheduler import is_auto_health_check_enabled, run_auto_health_check_loop
from app.storage.json_store import ensure_store_file, get_hosts_path, get_projects_path


BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    ensure_store_file(get_projects_path())
    ensure_store_file(get_hosts_path())
    auto_health_check_stop_event = asyncio.Event()
    auto_health_check_task = None
    if is_auto_health_check_enabled():
        auto_health_check_task = asyncio.create_task(
            run_auto_health_check_loop(auto_health_check_stop_event)
        )
    yield
    auto_health_check_stop_event.set()
    if auto_health_check_task is not None:
        await auto_health_check_task


def create_app(*, use_lifespan: bool = True) -> FastAPI:
    lifespan = app_lifespan if use_lifespan else None
    app = FastAPI(title="ops-hub", version="0.1.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
    app.include_router(hosts_router)
    app.include_router(projects_router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "service": "ops-hub"}

    @app.get("/dashboard")
    async def dashboard(request: Request):
        return FileResponse(BASE_DIR / "templates" / "dashboard.html")

    return app


app = create_app()
