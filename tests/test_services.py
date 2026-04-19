import os
import sys
import tempfile
import unittest
import asyncio
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
from requests import HTTPError


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


class OpsHubApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["OPS_HUB_PROJECTS_PATH"] = os.path.join(self.tempdir.name, "projects.json")
        os.environ["OPS_HUB_HOSTS_PATH"] = os.path.join(self.tempdir.name, "hosts.json")
        os.environ["OPS_HUB_AUTO_HEALTH_CHECK_ENABLED"] = "false"
        from app.main import create_app

        self.app = create_app(use_lifespan=False)

    def tearDown(self) -> None:
        os.environ.pop("OPS_HUB_PROJECTS_PATH", None)
        os.environ.pop("OPS_HUB_HOSTS_PATH", None)
        os.environ.pop("OPS_HUB_AUTO_HEALTH_CHECK_ENABLED", None)
        self.tempdir.cleanup()

    def request(self, method: str, path: str, **kwargs):
        async def send_request():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(send_request())

    def test_create_project_requires_existing_host(self) -> None:
        response = self.request(
            "POST",
            "/projects",
            json={
                "slug": "janus",
                "title": "Janus",
                "deployment_host": "srv",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unknown deployment_host", response.json()["detail"])

    def test_health_check_reports_healthy_when_urls_respond(self) -> None:
        self.request(
            "POST",
            "/hosts",
            json={
                "slug": "srv",
                "title": "Server",
                "transport": "none",
            },
        )
        self.request(
            "POST",
            "/projects",
            json={
                "slug": "janus",
                "title": "Janus",
                "deployment_host": "srv",
                "health_public_url": "https://example.com/public-health",
                "health_private_url": "https://example.com/private-health",
            },
        )

        response_ok = Mock(status_code=200)
        with patch("app.domain.health_service.requests.get", return_value=response_ok):
            response = self.request("POST", "/projects/janus/health-check")

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["summary"], "healthy")
        self.assertEqual(payload["checks"]["public"]["status"], "healthy")
        self.assertEqual(payload["checks"]["private"]["status"], "healthy")

    def test_health_check_persists_cached_summary_to_project_record(self) -> None:
        self.request(
            "POST",
            "/hosts",
            json={
                "slug": "srv",
                "title": "Server",
                "transport": "none",
            },
        )
        self.request(
            "POST",
            "/projects",
            json={
                "slug": "janus",
                "title": "Janus",
                "deployment_host": "srv",
                "health_public_url": "https://example.com/public-health",
                "health_private_url": "https://example.com/private-health",
            },
        )

        response_ok = Mock(status_code=200)
        with patch("app.domain.health_service.requests.get", return_value=response_ok):
            health_response = self.request("POST", "/projects/janus/health-check")

        self.assertEqual(health_response.status_code, 200)

        projects_response = self.request("GET", "/projects")
        projects_payload = projects_response.json()
        janus_project = next(
            project_payload
            for project_payload in projects_payload["projects"]
            if project_payload["slug"] == "janus"
        )

        self.assertEqual(janus_project["last_health_summary"], "healthy")
        self.assertTrue(janus_project["last_health_checked_at"])
        self.assertEqual(janus_project["last_health_result"]["summary"], "healthy")

    def test_create_http_host_requires_token_env_var(self) -> None:
        response = self.request(
            "POST",
            "/hosts",
            json={
                "slug": "desk",
                "title": "Desk",
                "transport": "http",
                "runner_url": "http://runner.local:8051",
                "token_env_var": "",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("token_env_var", response.json()["detail"])

    def test_get_hosts_includes_runner_health_for_http_host(self) -> None:
        create_response = self.request(
            "POST",
            "/hosts",
            json={
                "slug": "desk",
                "title": "Desk",
                "transport": "http",
                "runner_url": "http://runner.local:8051",
                "token_env_var": "DESK_RUNNER_TOKEN",
            },
        )
        self.assertEqual(create_response.status_code, 200)

        runner_health_response = Mock()
        runner_health_response.raise_for_status.return_value = None
        runner_health_response.text = '{"ok": true, "checked_at": "2026-04-18T10:00:00Z", "detail": "Runner reachable."}'
        runner_health_response.json.return_value = {
            "ok": True,
            "checked_at": "2026-04-18T10:00:00Z",
            "detail": "Runner reachable.",
        }

        with patch("app.domain.runner_client.requests.get", return_value=runner_health_response) as get_mock:
            response = self.request("GET", "/hosts")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["hosts"][0]["runner_health"]["status"], "healthy")
        self.assertTrue(payload["hosts"][0]["runner_health"]["ok"])
        self.assertEqual(payload["hosts"][0]["runner_health"]["transport"], "http")
        self.assertEqual(payload["hosts"][0]["runner_health"]["endpoint"], "http://runner.local:8051")
        self.assertEqual(get_mock.call_args.args[0], "http://runner.local:8051/health")

    def test_get_hosts_reports_unconfigured_runner_health_for_none_transport(self) -> None:
        create_response = self.request(
            "POST",
            "/hosts",
            json={
                "slug": "srv",
                "title": "Server",
                "transport": "none",
            },
        )
        self.assertEqual(create_response.status_code, 200)

        response = self.request("GET", "/hosts")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["hosts"][0]["runner_health"]["status"], "unconfigured")
        self.assertFalse(payload["hosts"][0]["runner_health"]["ok"])

    def test_project_action_runs_local_restart_command(self) -> None:
        self.request(
            "POST",
            "/hosts",
            json={
                "slug": "srv",
                "title": "Server",
                "transport": "none",
            },
        )
        self.request(
            "POST",
            "/projects",
            json={
                "slug": "janus",
                "title": "Janus",
                "deployment_host": "srv",
                "runtime_path": "/tmp/janus",
                "restart_command": "docker compose restart",
            },
        )

        completed_process = Mock(returncode=0, stdout="restarted\n", stderr="")
        with patch("app.domain.action_service.subprocess.run", return_value=completed_process) as run_mock:
            response = self.request("POST", "/projects/janus/actions", json={"action": "restart"})

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["action"], "restart")
        self.assertEqual(payload["project_slug"], "janus")
        self.assertEqual(payload["execution_mode"], "local")
        self.assertFalse(payload["dry_run"])
        self.assertEqual(payload["stdout"], "restarted\n")
        self.assertEqual(run_mock.call_args.kwargs["cwd"], "/tmp/janus")

    def test_project_action_dry_run_does_not_execute_command(self) -> None:
        self.request(
            "POST",
            "/hosts",
            json={
                "slug": "srv",
                "title": "Server",
                "transport": "none",
            },
        )
        self.request(
            "POST",
            "/projects",
            json={
                "slug": "janus",
                "title": "Janus",
                "deployment_host": "srv",
                "runtime_path": "/tmp/janus",
                "restart_command": "docker compose restart",
            },
        )

        with patch("app.domain.action_service.subprocess.run") as run_mock:
            response = self.request(
                "POST",
                "/projects/janus/actions",
                json={"action": "restart", "dry_run": True},
            )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["execution_mode"], "local")
        self.assertEqual(payload["command"], "docker compose restart")
        run_mock.assert_not_called()

    def test_project_action_returns_failed_result_for_missing_runtime_path(self) -> None:
        self.request(
            "POST",
            "/hosts",
            json={
                "slug": "srv",
                "title": "Server",
                "transport": "none",
            },
        )
        self.request(
            "POST",
            "/projects",
            json={
                "slug": "janus",
                "title": "Janus",
                "deployment_host": "srv",
                "runtime_path": "/definitely/missing/path",
                "restart_command": "docker compose restart",
            },
        )

        with patch(
            "app.domain.action_service.subprocess.run",
            side_effect=FileNotFoundError("No such file or directory: '/definitely/missing/path'"),
        ):
            response = self.request("POST", "/projects/janus/actions", json={"action": "restart"})

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["project_slug"], "janus")
        self.assertEqual(payload["execution_mode"], "local")
        self.assertIsNone(payload["exit_code"])
        self.assertIn("/definitely/missing/path", payload["stderr"])

    def test_project_logs_action_uses_runner_run_endpoint_for_socket_hosts(self) -> None:
        self.request(
            "POST",
            "/hosts",
            json={
                "slug": "srv",
                "title": "Server",
                "transport": "socket",
                "runner_socket_path": "/tmp/ops-hub.sock",
            },
        )
        self.request(
            "POST",
            "/projects",
            json={
                "slug": "janus",
                "title": "Janus",
                "deployment_host": "srv",
                "runtime_path": "/srv/stacks/janus",
                "logs_command": "docker compose logs --tail 100",
            },
        )

        with patch(
            "app.domain.action_service.post_runner_request",
            return_value={
                "ok": True,
                "exit_code": 0,
                "stdout": "logs\n",
                "stderr": "",
                "ran_at": "2026-04-19T06:10:00Z",
            },
        ) as post_runner_request_mock:
            response = self.request("POST", "/projects/janus/actions", json={"action": "logs"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(post_runner_request_mock.call_args.kwargs["path"], "/run")

    def test_project_logs_action_returns_failed_result_when_runner_returns_http_error(self) -> None:
        self.request(
            "POST",
            "/hosts",
            json={
                "slug": "desk",
                "title": "Desk",
                "transport": "http",
                "runner_url": "http://runner.local:8051",
                "token_env_var": "DESK_RUNNER_TOKEN",
            },
        )
        self.request(
            "POST",
            "/projects",
            json={
                "slug": "sakura",
                "title": "Sakura",
                "deployment_host": "desk",
                "runtime_path": "/srv/stacks/sakura",
                "logs_command": "docker compose logs --tail 100",
            },
        )

        runner_error = HTTPError("404 runner failure")
        runner_error.response = Mock(text='{"detail":"runner failed"}')

        with patch(
            "app.domain.action_service.post_runner_request",
            side_effect=runner_error,
        ):
            response = self.request("POST", "/projects/sakura/actions", json={"action": "logs"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertIn("runner failed", payload["stderr"])


class OpsHubCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["OPS_HUB_PROJECTS_PATH"] = os.path.join(self.tempdir.name, "projects.json")
        os.environ["OPS_HUB_HOSTS_PATH"] = os.path.join(self.tempdir.name, "hosts.json")
        os.environ["OPS_HUB_AUTO_HEALTH_CHECK_ENABLED"] = "false"

        from app.domain.host_service import create_host
        from app.domain.project_service import create_project
        from app.models.host_models import HostUpsertRequest
        from app.models.project_models import ProjectUpsertRequest

        create_host(
            HostUpsertRequest(
                slug="srv",
                title="Server",
                transport="none",
            )
        )
        create_project(
            ProjectUpsertRequest(
                slug="janus",
                title="Janus",
                deployment_host="srv",
                runtime_path="/tmp/janus",
                restart_command="docker compose restart",
            )
        )

    def tearDown(self) -> None:
        os.environ.pop("OPS_HUB_PROJECTS_PATH", None)
        os.environ.pop("OPS_HUB_HOSTS_PATH", None)
        os.environ.pop("OPS_HUB_AUTO_HEALTH_CHECK_ENABLED", None)
        self.tempdir.cleanup()

    def test_cli_projects_action_dry_run_json_output(self) -> None:
        import ops_hub

        captured_stdout = StringIO()
        captured_stderr = StringIO()

        with patch("sys.stdout", captured_stdout), patch("sys.stderr", captured_stderr):
            exit_code = ops_hub.main(
                ["projects", "action", "janus", "restart", "--dry-run", "--json"]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(captured_stderr.getvalue(), "")
        payload = __import__("json").loads(captured_stdout.getvalue())
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["project_slug"], "janus")
        self.assertEqual(payload["execution_mode"], "local")

    def test_cli_projects_action_returns_nonzero_for_failed_action(self) -> None:
        import ops_hub

        captured_stdout = StringIO()
        captured_stderr = StringIO()

        with patch(
            "app.domain.action_service.subprocess.run",
            side_effect=FileNotFoundError("No such file or directory: '/tmp/janus'"),
        ):
            with patch("sys.stdout", captured_stdout), patch("sys.stderr", captured_stderr):
                exit_code = ops_hub.main(["projects", "action", "janus", "restart", "--json"])

        self.assertEqual(exit_code, 0)
        payload = __import__("json").loads(captured_stdout.getvalue())
        self.assertFalse(payload["ok"])
        self.assertIn("/tmp/janus", payload["stderr"])
        self.assertEqual(captured_stderr.getvalue(), "")


class RunnerClientTests(unittest.TestCase):
    def test_socket_runner_raises_for_non_2xx_response(self) -> None:
        from app.domain.runner_client import post_runner_request
        from app.models.host_models import HostRecord
        from requests import HTTPError

        host_record = HostRecord(
            slug="srv",
            title="Server",
            transport="socket",
            runner_socket_path="/tmp/ops-hub.sock",
        )

        mocked_response = Mock()
        mocked_response.status = 500
        mocked_response.read.return_value = b'{"detail":"runner exploded"}'

        mocked_connection = Mock()
        mocked_connection.getresponse.return_value = mocked_response

        with patch("app.domain.runner_client.UnixHttpConnection", return_value=mocked_connection):
            with self.assertRaises(HTTPError) as raised_error:
                post_runner_request(
                    host_record=host_record,
                    path="/check-url",
                    payload={"url": "https://example.com/health"},
                )

        self.assertEqual(raised_error.exception.response.status_code, 500)
        self.assertIn("runner exploded", raised_error.exception.response.text)


class JsonStoreTests(unittest.TestCase):
    def test_write_store_data_keeps_existing_file_when_replace_fails(self) -> None:
        from app.storage.json_store import load_store_data, write_store_data

        with tempfile.TemporaryDirectory() as temporary_directory:
            store_path = Path(temporary_directory) / "projects.json"
            store_path.write_text('[{"slug": "existing"}]\n', encoding="utf-8")

            with patch("pathlib.Path.replace", side_effect=OSError("disk said no")):
                with self.assertRaises(OSError):
                    write_store_data(store_path, [{"slug": "updated"}])

            self.assertEqual(load_store_data(store_path), [{"slug": "existing"}])

    def test_ensure_store_file_bootstraps_projects_from_seed_file(self) -> None:
        from app.storage.json_store import ensure_store_file, load_store_data

        with tempfile.TemporaryDirectory() as temporary_directory:
            runtime_directory = Path(temporary_directory) / "runtime"
            runtime_directory.mkdir(parents=True, exist_ok=True)
            seed_path = runtime_directory / "projects.seed.json"
            store_path = runtime_directory / "projects.json"
            seed_path.write_text('[{"slug": "seeded-project"}]\n', encoding="utf-8")

            ensure_store_file(store_path)

            self.assertEqual(load_store_data(store_path), [{"slug": "seeded-project"}])

    def test_ensure_store_file_bootstraps_hosts_from_seed_file(self) -> None:
        from app.storage.json_store import ensure_store_file, load_store_data

        with tempfile.TemporaryDirectory() as temporary_directory:
            runtime_directory = Path(temporary_directory) / "runtime"
            runtime_directory.mkdir(parents=True, exist_ok=True)
            seed_path = runtime_directory / "hosts.seed.json"
            store_path = runtime_directory / "hosts.json"
            seed_path.write_text('[{"slug": "seeded-host"}]\n', encoding="utf-8")

            ensure_store_file(store_path)

            self.assertEqual(load_store_data(store_path), [{"slug": "seeded-host"}])


class HealthSchedulerTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("OPS_HUB_AUTO_HEALTH_CHECK_ENABLED", None)
        os.environ.pop("OPS_HUB_AUTO_HEALTH_CHECK_INTERVAL_SECONDS", None)

    def test_auto_health_check_enabled_defaults_to_true(self) -> None:
        from app.domain.health_scheduler import is_auto_health_check_enabled

        self.assertTrue(is_auto_health_check_enabled())

    def test_auto_health_check_enabled_accepts_false_like_values(self) -> None:
        from app.domain.health_scheduler import is_auto_health_check_enabled

        os.environ["OPS_HUB_AUTO_HEALTH_CHECK_ENABLED"] = "off"

        self.assertFalse(is_auto_health_check_enabled())

    def test_auto_health_check_interval_uses_minimum_floor(self) -> None:
        from app.domain.health_scheduler import get_auto_health_check_interval_seconds

        os.environ["OPS_HUB_AUTO_HEALTH_CHECK_INTERVAL_SECONDS"] = "5"

        self.assertEqual(get_auto_health_check_interval_seconds(), 30)

    def test_auto_health_check_sweep_persists_each_snapshot(self) -> None:
        from app.domain.health_scheduler import run_auto_health_check_sweep

        first_project_record = Mock(slug="janus")
        second_project_record = Mock(slug="atlas")
        janus_snapshot = {"summary": "healthy"}
        atlas_snapshot = {"summary": "down"}

        with patch(
            "app.domain.health_scheduler.list_projects",
            return_value=[first_project_record, second_project_record],
        ), patch(
            "app.domain.health_scheduler.run_project_health_check",
            side_effect=[janus_snapshot, atlas_snapshot],
        ) as run_project_health_check_mock, patch(
            "app.domain.health_scheduler.save_project_health_snapshot"
        ) as save_project_health_snapshot_mock:
            run_auto_health_check_sweep()

        self.assertEqual(run_project_health_check_mock.call_count, 2)
        save_project_health_snapshot_mock.assert_any_call("janus", janus_snapshot)
        save_project_health_snapshot_mock.assert_any_call("atlas", atlas_snapshot)

    def test_auto_health_check_sweep_continues_after_project_failure(self) -> None:
        from app.domain.health_scheduler import run_auto_health_check_sweep

        first_project_record = Mock(slug="janus")
        second_project_record = Mock(slug="atlas")
        atlas_snapshot = {"summary": "healthy"}

        with patch(
            "app.domain.health_scheduler.list_projects",
            return_value=[first_project_record, second_project_record],
        ), patch(
            "app.domain.health_scheduler.run_project_health_check",
            side_effect=[RuntimeError("boom"), atlas_snapshot],
        ), patch(
            "app.domain.health_scheduler.save_project_health_snapshot"
        ) as save_project_health_snapshot_mock:
            run_auto_health_check_sweep()

        save_project_health_snapshot_mock.assert_called_once_with("atlas", atlas_snapshot)
