import argparse
import json
import sys

from app.domain.action_service import run_project_action
from app.domain.health_service import run_project_health_check
from app.domain.host_service import get_host, list_hosts
from app.domain.project_service import get_project, list_projects


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ops-hub", description="Operate projects and hosts.")
    parser.add_argument("--json", action="store_true", dest="json_output")

    subparsers = parser.add_subparsers(dest="resource_name", required=True)

    projects_parser = subparsers.add_parser("projects")
    projects_subparsers = projects_parser.add_subparsers(dest="project_command_name", required=True)

    projects_subparsers.add_parser("list").add_argument("--json", action="store_true", dest="json_output")

    show_project_parser = projects_subparsers.add_parser("show")
    show_project_parser.add_argument("project_slug")
    show_project_parser.add_argument("--json", action="store_true", dest="json_output")

    health_check_parser = projects_subparsers.add_parser("health-check")
    health_check_parser.add_argument("project_slug")
    health_check_parser.add_argument("--json", action="store_true", dest="json_output")

    action_parser = projects_subparsers.add_parser("action")
    action_parser.add_argument("project_slug")
    action_parser.add_argument("action_name", choices=["deploy", "start", "restart", "stop", "logs"])
    action_parser.add_argument("--dry-run", action="store_true")
    action_parser.add_argument("--json", action="store_true", dest="json_output")

    hosts_parser = subparsers.add_parser("hosts")
    hosts_subparsers = hosts_parser.add_subparsers(dest="host_command_name", required=True)

    hosts_subparsers.add_parser("list").add_argument("--json", action="store_true", dest="json_output")

    show_host_parser = hosts_subparsers.add_parser("show")
    show_host_parser.add_argument("host_slug")
    show_host_parser.add_argument("--json", action="store_true", dest="json_output")

    return parser


def should_render_json(parsed_args: argparse.Namespace) -> bool:
    return bool(getattr(parsed_args, "json_output", False))


def print_output(payload: dict | list[dict], json_output: bool) -> int:
    if json_output:
        print(json.dumps(payload, indent=2))
        return 0

    if isinstance(payload, list):
        for item in payload:
            print(f"{item['slug']}: {item['title']}")
        return 0

    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            print(f"{key}:")
            print(json.dumps(value, indent=2))
            continue
        print(f"{key}: {value}")
    return 0


def handle_projects_command(parsed_args: argparse.Namespace) -> int:
    if parsed_args.project_command_name == "list":
        project_payload = [project.model_dump() for project in list_projects()]
        return print_output(project_payload, should_render_json(parsed_args))

    if parsed_args.project_command_name == "show":
        project_record = get_project(parsed_args.project_slug)
        if project_record is None:
            print(f"Project '{parsed_args.project_slug}' not found.", file=sys.stderr)
            return 1
        return print_output(project_record.model_dump(), should_render_json(parsed_args))

    if parsed_args.project_command_name == "health-check":
        project_record = get_project(parsed_args.project_slug)
        if project_record is None:
            print(f"Project '{parsed_args.project_slug}' not found.", file=sys.stderr)
            return 1
        return print_output(run_project_health_check(project_record), should_render_json(parsed_args))

    if parsed_args.project_command_name == "action":
        project_record = get_project(parsed_args.project_slug)
        if project_record is None:
            print(f"Project '{parsed_args.project_slug}' not found.", file=sys.stderr)
            return 1
        try:
            action_payload = run_project_action(
                project_record,
                parsed_args.action_name,
                dry_run=parsed_args.dry_run,
            )
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 1
        return print_output(action_payload, should_render_json(parsed_args))

    print(f"Unknown projects command '{parsed_args.project_command_name}'.", file=sys.stderr)
    return 1


def handle_hosts_command(parsed_args: argparse.Namespace) -> int:
    if parsed_args.host_command_name == "list":
        host_payload = [host.model_dump() for host in list_hosts()]
        return print_output(host_payload, should_render_json(parsed_args))

    if parsed_args.host_command_name == "show":
        host_record = get_host(parsed_args.host_slug)
        if host_record is None:
            print(f"Host '{parsed_args.host_slug}' not found.", file=sys.stderr)
            return 1
        return print_output(host_record.model_dump(), should_render_json(parsed_args))

    print(f"Unknown hosts command '{parsed_args.host_command_name}'.", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parsed_args = parser.parse_args(argv)

    if parsed_args.resource_name == "projects":
        return handle_projects_command(parsed_args)
    if parsed_args.resource_name == "hosts":
        return handle_hosts_command(parsed_args)

    print(f"Unknown resource '{parsed_args.resource_name}'.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
