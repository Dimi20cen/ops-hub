# ops-hub

`ops-hub` is a small FastAPI control plane for project operations.

It does four things:
- stores projects
- stores hosts
- runs health checks
- triggers project actions: `deploy`, `start`, `restart`, `stop`, `logs`

## Start Here

- `README.md`: entry point for human readers
- `AGENTS.md`: operating instructions for coding agents
- `VISION.md`: stable direction for the repo
- `docs/contracts.md`: source of truth for what consumers can rely on
- `docs/specs/`: source of truth for expected behavior
- `docs/decisions/`: why important choices were made

## Structure

```text
ops-hub/
  docs/
    specs/
    decisions/
    contracts.md
  AGENTS.md
  VISION.md
  app/
    api/
    domain/
    models/
    storage/
    main.py
  runtime/
    projects.json
    hosts.json
  tests/
  requirements.txt
  run.py
```

## Local Run

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:8011/docs`.
Open `http://127.0.0.1:8011/dashboard` for the operator UI.

## Deploy Shape

`ops-hub` is set up to deploy on `srv` in the same style as the existing stack apps:

- repo path: `/srv/stacks/ops-hub`
- runtime path: `/srv/stacks/ops-hub/runtime`
- container port: `8011`
- deploy command: `/usr/bin/bash /srv/stacks/ops-hub/bin/deploy.sh`

Expected files for the stack:

- `.env`
- `docker-compose.yml`
- `Dockerfile`
- `runtime/projects.json`
- `runtime/hosts.json`
- `runtime/projects.seed.json`
- `runtime/hosts.seed.json`

The `srv` host runner socket is expected to be mounted from:

- host path: `/srv/stacks/hq/runtime/action-runner.sock`
- container path: `/app/runtime/action-runner.sock`

Bootstrap from the example env file:

```bash
cp .env.example .env
chmod +x bin/deploy.sh
```

Live runtime files are created from the seed files only when missing:

- `runtime/projects.seed.json` -> `runtime/projects.json`
- `runtime/hosts.seed.json` -> `runtime/hosts.json`

The live runtime files are intentionally not tracked by Git.

## CLI

You can also use the local CLI directly:

```bash
python ops_hub.py projects list
python ops_hub.py projects show janus --json
python ops_hub.py projects health-check janus --json
python ops_hub.py projects action janus restart --dry-run --json
python ops_hub.py hosts list
```

## Environment Variables

- `OPS_HUB_HOST`: server bind host, defaults to `127.0.0.1`
- `OPS_HUB_PORT`: server bind port, defaults to `8011`
- `OPS_HUB_PROJECTS_PATH`: custom project JSON path
- `OPS_HUB_HOSTS_PATH`: custom host JSON path
- `OPS_HUB_AUTO_HEALTH_CHECK_ENABLED`: enable automatic project health sweeps, defaults to `true`
- `OPS_HUB_AUTO_HEALTH_CHECK_INTERVAL_SECONDS`: automatic health sweep interval, defaults to `300`, minimum `30`

## API Summary

- `GET /health`
- `GET /projects`
- `POST /projects`
- `PUT /projects/{slug}`
- `DELETE /projects/{slug}`
- `POST /projects/{slug}/health-check`
- `POST /projects/{slug}/actions`
- `GET /hosts`
- `POST /hosts`
- `PUT /hosts/{slug}`
- `DELETE /hosts/{slug}`

Action response details live in `docs/contracts.md`.
Host validation and runner health behavior live in `docs/specs/hosts.md`.
