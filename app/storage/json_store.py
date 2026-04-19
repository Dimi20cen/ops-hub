import json
import os
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_PROJECTS_PATH = BASE_DIR / "runtime" / "projects.json"
DEFAULT_HOSTS_PATH = BASE_DIR / "runtime" / "hosts.json"
DEFAULT_PROJECTS_SEED_PATH = BASE_DIR / "runtime" / "projects.seed.json"
DEFAULT_HOSTS_SEED_PATH = BASE_DIR / "runtime" / "hosts.seed.json"


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


def get_seed_path_for_store(store_path: Path) -> Path | None:
    if store_path == DEFAULT_PROJECTS_PATH:
        return DEFAULT_PROJECTS_SEED_PATH
    if store_path == DEFAULT_HOSTS_PATH:
        return DEFAULT_HOSTS_SEED_PATH

    if store_path.name == "projects.json":
        sibling_seed_path = store_path.with_name("projects.seed.json")
        if sibling_seed_path.exists():
            return sibling_seed_path
    if store_path.name == "hosts.json":
        sibling_seed_path = store_path.with_name("hosts.seed.json")
        if sibling_seed_path.exists():
            return sibling_seed_path

    return None


def ensure_store_file(store_path: Path) -> Path:
    store_path.parent.mkdir(parents=True, exist_ok=True)
    if not store_path.exists():
        seed_path = get_seed_path_for_store(store_path)
        if seed_path and seed_path.exists():
            store_path.write_text(seed_path.read_text(encoding="utf-8"), encoding="utf-8")
        else:
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
