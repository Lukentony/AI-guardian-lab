"""guardian-lab: first-run setup, diagnostics and deterministic demo."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .checks import (
    Check,
    check_docker,
    check_ports,
    check_state_dirs,
    compose_up,
    create_state_dirs,
    run_doctor,
)
from .demo import run_demo
from .envfile import EnvError, generate_env, read_env_file, validate_env, write_env_file

DEFAULT_ROOT = Path(__file__).resolve().parents[2]


def _print_checks(checks: Sequence[Check]) -> None:
    for check in checks:
        print(f"{check.status.upper():<4} {check.component:<8} {check.name:<24} {check.detail}")
    failures = [check for check in checks if not check.ok and check.required]
    if failures:
        print("\nHints:")
        for check in failures:
            if check.hint:
                print(f"- {check.component}/{check.name}: {check.hint}")


def _paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    root = Path(args.root).expanduser().resolve()
    env_file = Path(args.env_file).expanduser()
    compose_file = Path(args.compose_file).expanduser()
    if not env_file.is_absolute():
        env_file = root / env_file
    if not compose_file.is_absolute():
        compose_file = root / compose_file
    return root, env_file, compose_file


def _cmd_setup(args: argparse.Namespace) -> int:
    root, env_file, compose_file = _paths(args)
    if not root.is_dir():
        print(f"Repository root does not exist: {root}", file=sys.stderr)
        return 2

    if env_file.exists():
        if not args.reuse:
            print(
                f"{env_file} already exists. Preserve it, or pass --reuse to validate it.",
                file=sys.stderr,
            )
            return 2
        try:
            values = read_env_file(env_file)
        except EnvError as exc:
            print(f"Cannot read {env_file}: {exc}", file=sys.stderr)
            return 2
        issues = [issue for issue in validate_env(values, args.profile) if issue.level == "error"]
        if issues:
            for issue in issues:
                print(f"ERROR {issue.key}: {issue.message}", file=sys.stderr)
            return 2
        print(f"Existing configuration is valid: {env_file}")
    else:
        checks = check_docker()
        failures = [check for check in checks if not check.ok and check.required]
        if failures:
            _print_checks(checks)
            return 1

        uid = os.getuid() if hasattr(os, "getuid") else 1000
        gid = os.getgid() if hasattr(os, "getgid") else 1000
        values = generate_env(args.profile, uid, gid)

        port_checks = check_ports(values, allow_running=False)
        port_failures = [check for check in port_checks if not check.ok and check.required]
        if port_failures:
            _print_checks(port_checks)
            print("Stop the process using the port, then run setup again.", file=sys.stderr)
            return 1

        try:
            create_state_dirs(root)
        except OSError as exc:
            print(f"Cannot create state directories: {exc}", file=sys.stderr)
            return 1
        state_failures = [check for check in check_state_dirs(root) if not check.ok and check.required]
        if state_failures:
            _print_checks(state_failures)
            return 1

        try:
            write_env_file(env_file, values)
        except (EnvError, OSError) as exc:
            print(f"Cannot create {env_file}: {exc}", file=sys.stderr)
            return 1
        print(f"Created {env_file} with mode 600. Secrets are not printed.")

    if not args.no_start:
        if compose_up(root, env_file, compose_file, build=True) != 0:
            print("The stack did not start. Check: docker compose logs --tail=100 guardian", file=sys.stderr)
            return 1

    print("")
    print("Next steps:")
    print("  ./guardian-lab doctor")
    print("  ./guardian-lab demo")
    print(f"  Dashboard: http://127.0.0.1:{values.get('UI_PORT', '8081')}")
    print("Credentials are in .env; they are not shown here.")
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    root, env_file, compose_file = _paths(args)
    checks = run_doctor(
        root,
        env_file,
        compose_file,
        profile=args.profile,
        probe_models=args.probe_models,
    )
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_checks(checks)
    failures = [check for check in checks if not check.ok and check.required]
    return 1 if failures else 0


def _cmd_demo(args: argparse.Namespace) -> int:
    root, env_file, compose_file = _paths(args)
    return run_demo(
        root,
        env_file,
        compose_file,
        start=not args.no_start,
        build=not args.no_build,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guardian-lab",
        description="Set up, diagnose and demo AI Guardian Lab without executing commands.",
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="repository or release root")
    parser.add_argument("--env-file", type=Path, default=Path(".env"), help="configuration file")
    parser.add_argument(
        "--compose-file", type=Path, default=Path("docker-compose.yml"), help="Compose file"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup = subparsers.add_parser("setup", help="create .env and optional state directories")
    setup.add_argument("--profile", choices=("demo", "local-models"), default="demo")
    setup.add_argument("--no-start", action="store_true", help="write configuration only")
    setup.add_argument(
        "--reuse", action="store_true", help="validate an existing .env instead of creating one"
    )
    setup.set_defaults(func=_cmd_setup)

    doctor = subparsers.add_parser("doctor", help="check configuration, stack, audit and UI")
    doctor.add_argument("--json", action="store_true", help="machine-readable, redacted output")
    doctor.add_argument(
        "--probe-models",
        action="store_true",
        help="also probe Ollama reachability and model presence",
    )
    doctor.add_argument("--profile", choices=("demo", "local-models"), default="demo")
    doctor.set_defaults(func=_cmd_doctor)

    demo = subparsers.add_parser("demo", help="validate five fixed cases and inspect the audit")
    demo.add_argument("--no-start", action="store_true", help="do not start the stack")
    demo.add_argument("--no-build", action="store_true", help="reuse existing images")
    demo.set_defaults(func=_cmd_demo)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except EnvError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
