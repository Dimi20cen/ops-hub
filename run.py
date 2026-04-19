import os
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def main() -> None:
    host = os.getenv("OPS_HUB_HOST", "127.0.0.1")
    port = os.getenv("OPS_HUB_PORT", "8011")

    subprocess.call(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:create_app",
            "--host",
            host,
            "--port",
            port,
            "--factory",
            "--reload",
        ],
        cwd=BASE_DIR,
    )


if __name__ == "__main__":
    main()
