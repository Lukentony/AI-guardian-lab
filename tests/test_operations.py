import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("scenario", ["local", "none"])
def test_installer_uses_compose_and_preserves_existing_config(tmp_path, scenario):
    shutil.copyfile(ROOT / "install.sh", tmp_path / "install.sh")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    scripts = {
        "docker": '#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_DOCKER_LOG"\nexit 0\n',
        "docker-compose": '#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_DOCKER_LOG"\nexit 0\n',
        "ollama": "#!/bin/sh\nexit 0\n",
        "sleep": "#!/bin/sh\nexit 0\n",
        "curl": """#!/bin/sh
case "$*" in
  *api/tags*)
    [ "$TEST_SCENARIO" = local ] || exit 1
    printf '%s' '{"models":[{"name":"test-local-model"}]}'
    ;;
esac
exit 0
""",
    }
    for name, content in scripts.items():
        path = binaries / name
        path.write_text(content)
        path.chmod(0o700)
    environment = {
        "PATH": f"{binaries}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "NON_INTERACTIVE": "true",
        "TEST_SCENARIO": scenario,
        "TEST_DOCKER_LOG": str(tmp_path / "commands.log"),
    }
    first = subprocess.run(
        ["bash", str(tmp_path / "install.sh")],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        timeout=15,
    )
    assert first.returncode == 0
    config = (tmp_path / ".env").read_bytes()
    assert (tmp_path / ".env").stat().st_mode & 0o777 == 0o600
    commands = (tmp_path / "commands.log").read_text()
    assert "build guardian agent ui" in commands
    assert "docker build" not in commands
    assert b"EXECUTE_COMMANDS=false" in config and b"SANDBOX_MODE=" not in config
    if scenario == "local":
        assert b"LLM_MODEL_CODER=test-local-model" in config
    second = subprocess.run(
        ["bash", str(tmp_path / "install.sh")],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        timeout=15,
    )
    assert second.returncode != 0
    assert (tmp_path / ".env").read_bytes() == config


def test_compose_static_security_and_build_contexts():
    config = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = config["services"]
    assert services["guardian"]["build"]["context"] == "."
    assert all(
        "curl" not in str(services[name]["healthcheck"]) for name in ("guardian", "agent", "ui")
    )
    assert services["ui"]["ports"][0].startswith("127.0.0.1:")
    assert "volumes" not in services["ui"]
    assert "ports" not in services["system-one"]
    assert services["system-one"]["profiles"] == ["system-one", "full"]
    assert services["llama"]["profiles"] == ["full"]
    assert "${INTENT_LLM_TIMEOUT_SECONDS" in services["guardian"]["environment"][
        "INTENT_LLM_TIMEOUT_SECONDS"
    ]
    assert " " not in services["agent"]["tmpfs"][0]
    for service in services.values():
        if "build" not in service:
            continue
        context = ROOT / service["build"]["context"]
        dockerfile = context / service["build"].get("dockerfile", "Dockerfile")
        assert dockerfile.is_file()
        for line in dockerfile.read_text().splitlines():
            if line.startswith("COPY "):
                source = line.split()[1]
                assert (context / source).exists()


def test_optional_model_gate_stops_before_import_or_network(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "system-one/serve.py")],
        env={"PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "not installed" in result.stderr or "not qualified" in result.stderr
    assert "ModuleNotFoundError" not in result.stderr
    for filename in ("bootstrap.sh", "qualification.py"):
        shutil.copyfile(ROOT / "system-one" / filename, tmp_path / filename)
    prepared = subprocess.run(
        ["sh", str(tmp_path / "bootstrap.sh")],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert prepared.returncode != 0
    assert not (tmp_path / ".venv").exists()
    dockerfile = (ROOT / "system-one/Dockerfile").read_text()
    assert dockerfile.index("RUN pip install") < dockerfile.index("RUN python qualification.py")


def test_verifier_fails_for_missing_database(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/verify_logs.py"),
            "--db",
            str(tmp_path / "missing.db"),
        ],
        env={"PATH": "/usr/bin:/bin"},
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert not (tmp_path / "missing.db").exists()
