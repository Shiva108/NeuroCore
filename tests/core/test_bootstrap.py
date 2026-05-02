import importlib.util
import io
import subprocess
import sys
from pathlib import Path


def load_bootstrap_module():
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "bootstrap.py"
    spec = importlib.util.spec_from_file_location("bootstrap_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


BOOTSTRAP = load_bootstrap_module()


def create_repo_scaffold(tmp_path: Path) -> None:
    (tmp_path / ".env.security-operator.example").write_text(
        "\n".join(
            [
                "NEUROCORE_DEFAULT_NAMESPACE=security-lab",
                "NEUROCORE_ALLOWED_BUCKETS=recon,targets,findings,payloads,reports,agents,ops",
                "NEUROCORE_DEFAULT_SENSITIVITY=restricted",
                "NEUROCORE_STORAGE_BACKEND=sqlite",
                "NEUROCORE_PRIMARY_STORE_PATH=data/neurocore.db",
                "NEUROCORE_SEALED_STORE_PATH=data/neurocore-sealed.db",
                "NEUROCORE_SEMANTIC_BACKEND=sentence-transformers",
                "NEUROCORE_ENABLE_ADMIN_SURFACE=false",
                "NEUROCORE_ENABLE_HTTP_ADAPTER=false",
                "NEUROCORE_ENABLE_MCP_ADAPTER=false",
                "NEUROCORE_ENABLE_DASHBOARD=false",
                "NEUROCORE_ENABLE_BACKGROUND_SUMMARIZATION=false",
                "NEUROCORE_ENABLE_MULTI_MODEL_CONSENSUS=false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "secrets.json.example").write_text("{}", encoding="utf-8")
    (tmp_path / "preferences.json.example").write_text("{}", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "security_workflow.py").write_text(
        "def print_readiness_summary(*, repo_root, env, stdout):\n"
        "    print('Readiness summary: semantic=ready; query=ready; report=not ready', file=stdout)\n"
        "    print('Report prerequisites still missing:', file=stdout)\n"
        "    print('- Consensus reporting disabled', file=stdout)\n"
        "    print('Local-only report generation can use the bundled mock provider at http://127.0.0.1:8787/v1.', file=stdout)\n",
        encoding="utf-8",
    )


class FakeRunner:
    def __init__(self, fail_on=None):
        self.fail_on = fail_on
        self.commands = []

    def __call__(self, command, cwd, env):
        self.commands.append({"command": command, "cwd": cwd, "env": env})
        if self.fail_on and self.fail_on(command):
            raise subprocess.CalledProcessError(returncode=1, cmd=command)
        if command[0] == sys.executable and command[1:3] == ["-m", "venv"]:
            venv_dir = Path(command[-1])
            python_path = BOOTSTRAP._venv_python_path(venv_dir)
            python_path.parent.mkdir(parents=True, exist_ok=True)
            python_path.write_text("", encoding="utf-8")


def test_bootstrap_creates_local_setup_files_and_runs_verification(tmp_path: Path):
    create_repo_scaffold(tmp_path)
    runner = FakeRunner()
    stdout = io.StringIO()

    exit_code = BOOTSTRAP.main(
        [],
        repo_root=tmp_path,
        stdout=stdout,
        stderr=io.StringIO(),
        runner=runner,
    )

    assert exit_code == 0
    assert (tmp_path / ".venv").exists()
    assert (tmp_path / ".env").exists()
    assert (tmp_path / "secrets.json").exists()
    assert (tmp_path / "preferences.json").exists()
    assert (tmp_path / "data").exists()

    commands = [entry["command"] for entry in runner.commands]
    assert [
        str(BOOTSTRAP._venv_python_path(tmp_path / ".venv")),
        "-m",
        "pip",
        "install",
        "-e",
        ".[dev,semantic]",
    ] in commands
    assert [
        str(BOOTSTRAP._venv_python_path(tmp_path / ".venv")),
        "-m",
        "pytest",
    ] in commands
    assert [
        str(BOOTSTRAP._venv_python_path(tmp_path / ".venv")),
        "-m",
        "neurocore.governance.validation",
    ] in commands
    assert "NeuroCore bootstrap is complete." in stdout.getvalue()
    assert "Readiness summary: semantic=ready; query=ready; report=not ready" in stdout.getvalue()
    assert "mock provider at http://127.0.0.1:8787/v1" in stdout.getvalue()


def test_bootstrap_preserves_existing_env_by_default(tmp_path: Path):
    create_repo_scaffold(tmp_path)
    env_path = tmp_path / ".env"
    env_path.write_text("NEUROCORE_DEFAULT_NAMESPACE=keep-me\n", encoding="utf-8")
    runner = FakeRunner()

    exit_code = BOOTSTRAP.main(
        ["--skip-verify"],
        repo_root=tmp_path,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
        runner=runner,
    )

    assert exit_code == 0
    assert (
        env_path.read_text(encoding="utf-8") == "NEUROCORE_DEFAULT_NAMESPACE=keep-me\n"
    )


def test_bootstrap_force_env_rewrites_profile(tmp_path: Path):
    create_repo_scaffold(tmp_path)
    env_path = tmp_path / ".env"
    env_path.write_text("NEUROCORE_DEFAULT_NAMESPACE=keep-me\n", encoding="utf-8")

    exit_code = BOOTSTRAP.main(
        ["--force-env", "--skip-verify"],
        repo_root=tmp_path,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
        runner=FakeRunner(),
    )

    assert exit_code == 0
    contents = env_path.read_text(encoding="utf-8")
    assert "NEUROCORE_DEFAULT_NAMESPACE=security-lab" in contents
    assert "NEUROCORE_STORAGE_BACKEND=sqlite" in contents


def test_bootstrap_generates_expected_security_profile_env(tmp_path: Path):
    create_repo_scaffold(tmp_path)
    runner = FakeRunner()

    exit_code = BOOTSTRAP.main(
        [],
        repo_root=tmp_path,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
        runner=runner,
    )

    assert exit_code == 0
    contents = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "NEUROCORE_DEFAULT_NAMESPACE=security-lab" in contents
    assert (
        "NEUROCORE_ALLOWED_BUCKETS=recon,targets,findings,payloads,reports,agents,ops"
        in contents
    )
    assert "NEUROCORE_SEMANTIC_BACKEND=sentence-transformers" in contents
    verify_commands = [
        entry for entry in runner.commands if entry["command"][1:3] == ["-m", "pytest"]
    ]
    assert verify_commands
    assert verify_commands[0]["env"]["NEUROCORE_DEFAULT_NAMESPACE"] == "security-lab"


def test_makefile_setup_target_uses_bootstrap_command():
    makefile = (Path(__file__).resolve().parents[2] / "Makefile").read_text(
        encoding="utf-8"
    )

    assert "setup:\n\tpython scripts/bootstrap.py\n" in makefile


def test_bootstrap_reports_readable_install_failures(tmp_path: Path):
    create_repo_scaffold(tmp_path)
    stderr = io.StringIO()

    exit_code = BOOTSTRAP.main(
        ["--skip-verify"],
        repo_root=tmp_path,
        stdout=io.StringIO(),
        stderr=stderr,
        runner=FakeRunner(
            fail_on=lambda command: command[1:5] == ["-m", "pip", "install", "-e"]
        ),
    )

    assert exit_code == 1
    assert (tmp_path / ".venv").exists()
    message = stderr.getvalue()
    assert "Bootstrap failed" in message
    assert "Failed command:" in message
    assert "editable install" in message


def test_bootstrap_wizard_rejects_invalid_namespace(tmp_path: Path):
    create_repo_scaffold(tmp_path)
    stderr = io.StringIO()

    exit_code = BOOTSTRAP.main(
        ["--wizard", "--skip-verify"],
        repo_root=tmp_path,
        stdout=io.StringIO(),
        stderr=stderr,
        input_fn=lambda prompt: "Bad Namespace",
        runner=FakeRunner(),
    )

    assert exit_code == 1
    assert "Namespace must start" in stderr.getvalue()


def test_bootstrap_recreates_incomplete_virtualenv(tmp_path: Path):
    create_repo_scaffold(tmp_path)
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / "stale.txt").write_text("stale", encoding="utf-8")
    runner = FakeRunner()
    stdout = io.StringIO()

    exit_code = BOOTSTRAP.main(
        ["--skip-verify"],
        repo_root=tmp_path,
        stdout=stdout,
        stderr=io.StringIO(),
        runner=runner,
    )

    assert exit_code == 0
    assert not (venv_dir / "stale.txt").exists()
    assert "recreating it" in stdout.getvalue()
