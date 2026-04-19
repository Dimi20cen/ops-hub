import json
import os
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_PROJECTS_PATH = BASE_DIR / "runtime" / "projects.json"
DEFAULT_HOSTS_PATH = BASE_DIR / "runtime" / "hosts.json"


def get_projects_path() -> Path:
    configured_path = os.getenv("OPS_HUB_PROJECTS_PATH")
    if configured_path:
        return Path(configured_path)
    return DEFAULT_PROJECTS_PATH


def get_hosts_path() -> Path:
    configured_path = os.getenv("OPS_HUB_HOSTS_PATH")
    if configured_path:
        return Path(configured_path)
    return DEFAULT_HOSTS_PATH


def ensure_store_file(store_path: Path) -> Path:
    store_path.parent.mkdir(parents=True, exist_ok=True)
    if not store_path.exists():
        store_path.write_text("[]\n", encoding="utf-8")
    return store_path


def load_store_data(store_path: Path) -> list[dict]:
    ensured_path = ensure_store_file(store_path)
    try:
        raw_payload = json.loads(ensured_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {ensured_path}: {error}") from error
    if not isinstance(raw_payload, list):
        raise ValueError(f"Expected a JSON array in {ensured_path}.")
    return raw_payload


def write_store_data(store_path: Path, records: list[dict]) -> None:
    ensured_path = ensure_store_file(store_path)
    serialized_records = f"{json.dumps(records, indent=2)}\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=ensured_path.parent,
        delete=False,
    ) as temporary_file:
        temporary_file.write(serialized_records)
        temporary_path = Path(temporary_file.name)
    temporary_path.replace(ensured_path)
