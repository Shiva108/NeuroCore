"""Bootstrap local NeuroCore development and security workflows."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, TextIO

DEFAULT_PROFILE = "security-operator"
NAMESPACE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
PROFILE_TEMPLATES = {
    "security-operator": ".env.security-operator.example",
}
LOCAL_TEMPLATE_FILES = (
    ("secrets.json.example", "secrets.json"),
    ("preferences.json.example", "preferences.json"),
)


class BootstrapError(RuntimeError):
    """Raised when bootstrap cannot complete safely."""

    def __init__(
        self,
        message: str,
        *,
        command: list[str] | None = None,
        remediation: str | None = None,
    ) -> None:
        super().__init__(message)
        self.command = command
        self.remediation = remediation


Runner = Callable[[list[str], Path, dict[str, str] | None], None]


def build_parser() -> argparse.ArgumentParser:
    """Create the bootstrap CLI parser."""
    parser = argparse.ArgumentParser(
        prog="python scripts/bootstrap.py",
        description="Set up a local NeuroCore workspace with security defaults.",
    )
    parser.add_argument(
        "--wizard",
        action="store_true",
        help="Prompt for namespace, .env overwrite, and verification choices.",
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        choices=sorted(PROFILE_TEMPLATES),
        help="Select the onboarding profile to apply.",
    )
    parser.add_argument(
        "--force-env",
        action="store_true",
        help="Overwrite an existing .env with the selected profile.",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip pytest and governance verification at the end of setup.",
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    repo_root: Path | None = None,
    input_fn: Callable[[str], str] = input,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    runner: Runner | None = None,
) -> int:
    """Run the local bootstrap workflow."""
    parser = build_parser()
    args = parser.parse_args(argv)
    root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    command_runner = runner or _run_subprocess

    try:
        run_bootstrap(
            args,
            repo_root=root,
            input_fn=input_fn,
            stdout=stdout,
            runner=command_runner,
        )
    except BootstrapError as exc:
        print(f"Bootstrap failed: {exc}", file=stderr)
        if exc.command:
            print(f"Failed command: {_format_command(exc.command)}", file=stderr)
        if exc.remediation:
            print(f"Try this: {exc.remediation}", file=stderr)
        return 1

    return 0


def run_bootstrap(
    args: argparse.Namespace,
    *,
    repo_root: Path,
    input_fn: Callable[[str], str],
    stdout: TextIO,
    runner: Runner,
) -> None:
    """Execute the bootstrap steps for a repo root."""
    print(
        f"Starting NeuroCore bootstrap with the {args.profile} profile.",
        file=stdout,
    )

    venv_dir = repo_root / ".venv"
    _ensure_virtualenv(venv_dir, repo_root=repo_root, stdout=stdout, runner=runner)
    venv_python = _venv_python_path(venv_dir)

    install_env = dict(os.environ)
    _run_checked(
        [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
        cwd=repo_root,
        env=install_env,
        runner=runner,
        remediation="Activate the virtual environment and confirm pip is available.",
    )
    _run_checked(
        [str(venv_python), "-m", "pip", "install", "-e", ".[dev,semantic]"],
        cwd=repo_root,
        env=install_env,
        runner=runner,
        remediation=(
            "Check internet access, Python build tooling, and the editable install"
            " metadata in pyproject.toml."
        ),
    )

    data_dir = repo_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"Ensured local runtime data directory at {data_dir}.", file=stdout)

    namespace = "security-lab"
    overwrite_env = args.force_env
    run_verification = not args.skip_verify
    env_path = repo_root / ".env"

    if args.wizard:
        namespace, overwrite_env, run_verification = _run_wizard(
            env_path=env_path,
            default_namespace=namespace,
            default_overwrite=overwrite_env,
            default_verify=run_verification,
            input_fn=input_fn,
            stdout=stdout,
        )

    _ensure_env_file(
        profile=args.profile,
        namespace=namespace,
        env_path=env_path,
        repo_root=repo_root,
        overwrite=overwrite_env,
        stdout=stdout,
    )
    for template_name, target_name in LOCAL_TEMPLATE_FILES:
        _copy_if_missing(
            source=repo_root / template_name,
            destination=repo_root / target_name,
            stdout=stdout,
        )

    if run_verification:
        runtime_env = dict(os.environ)
        runtime_env.update(_load_env_values(env_path))
        _run_checked(
            [str(venv_python), "-m", "pytest"],
            cwd=repo_root,
            env=runtime_env,
            runner=runner,
            remediation="Review the pytest output, then rerun bootstrap after fixing the failing test.",
        )
        _run_checked(
            [str(venv_python), "-m", "neurocore.governance.validation"],
            cwd=repo_root,
            env=runtime_env,
            runner=runner,
            remediation=(
                "Inspect the reported contract or secret-hygiene issue, adjust the"
                " local files, and rerun bootstrap."
            ),
        )
        print("Verification completed successfully.", file=stdout)
    else:
        print("Skipped verification at your request.", file=stdout)

    _print_next_steps(stdout)


def _run_wizard(
    *,
    env_path: Path,
    default_namespace: str,
    default_overwrite: bool,
    default_verify: bool,
    input_fn: Callable[[str], str],
    stdout: TextIO,
) -> tuple[str, bool, bool]:
    """Collect the limited v1 setup decisions interactively."""
    print("Running bootstrap wizard.", file=stdout)
    namespace = (
        input_fn(f"Namespace to write into .env [{default_namespace}]: ").strip()
        or default_namespace
    )
    _validate_namespace(namespace)

    overwrite = default_overwrite
    if env_path.exists() and not default_overwrite:
        overwrite = _prompt_yes_no(
            input_fn,
            "Overwrite the existing .env? [y/N]: ",
            default=False,
        )

    verify = default_verify
    if default_verify:
        verify = _prompt_yes_no(
            input_fn,
            "Run pytest and governance checks after setup? [Y/n]: ",
            default=True,
        )

    return namespace, overwrite, verify


def _ensure_virtualenv(
    venv_dir: Path,
    *,
    repo_root: Path,
    stdout: TextIO,
    runner: Runner,
) -> None:
    """Create the virtual environment if it is missing."""
    if _venv_python_path(venv_dir).exists():
        print(f"Reusing existing virtual environment at {venv_dir}.", file=stdout)
        return
    if venv_dir.exists():
        print(
            f"Virtual environment directory exists but is incomplete at {venv_dir}; "
            "recreating it.",
            file=stdout,
        )
        shutil.rmtree(venv_dir)

    print(f"Creating virtual environment at {venv_dir}.", file=stdout)
    _run_checked(
        [sys.executable, "-m", "venv", str(venv_dir)],
        cwd=repo_root,
        env=None,
        runner=runner,
        remediation="Install Python 3.11+ with the venv module available.",
    )


def _ensure_env_file(
    *,
    profile: str,
    namespace: str,
    env_path: Path,
    repo_root: Path,
    overwrite: bool,
    stdout: TextIO,
) -> None:
    """Create or preserve the local .env file from the selected profile."""
    existed_before = env_path.exists()
    if existed_before and not overwrite:
        print(f"Preserved existing environment file at {env_path}.", file=stdout)
        return

    template_name = PROFILE_TEMPLATES[profile]
    template_path = repo_root / template_name
    if not template_path.exists():
        raise BootstrapError(
            f"Missing bootstrap profile template: {template_name}",
            remediation="Restore the checked-in profile template before rerunning setup.",
        )

    env_path.write_text(
        _render_env_template(
            template_path.read_text(encoding="utf-8"),
            namespace=namespace,
        ),
        encoding="utf-8",
    )
    action = "Updated" if existed_before else "Wrote"
    print(f"{action} environment file at {env_path}.", file=stdout)


def _copy_if_missing(*, source: Path, destination: Path, stdout: TextIO) -> None:
    """Copy a local-only template if the target does not exist."""
    if not source.exists():
        raise BootstrapError(
            f"Missing local template file: {source.name}",
            remediation="Restore the checked-in example files before rerunning setup.",
        )
    if destination.exists():
        print(f"Preserved existing local file at {destination}.", file=stdout)
        return
    shutil.copyfile(source, destination)
    print(f"Created local file at {destination}.", file=stdout)


def _load_env_values(env_path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file into process environment values."""
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _render_env_template(template_text: str, *, namespace: str) -> str:
    """Return the profile template with the selected namespace applied."""
    _validate_namespace(namespace)
    rendered_lines = []
    replaced_namespace = False
    for line in template_text.splitlines():
        if line.startswith("NEUROCORE_DEFAULT_NAMESPACE="):
            rendered_lines.append(f"NEUROCORE_DEFAULT_NAMESPACE={namespace}")
            replaced_namespace = True
            continue
        rendered_lines.append(line)
    if not replaced_namespace:
        rendered_lines.append(f"NEUROCORE_DEFAULT_NAMESPACE={namespace}")
    return "\n".join(rendered_lines) + "\n"


def _venv_python_path(venv_dir: Path) -> Path:
    """Resolve the venv Python interpreter for the current platform."""
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run_checked(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None,
    runner: Runner,
    remediation: str,
) -> None:
    """Run a command and raise a bootstrap-specific error when it fails."""
    try:
        runner(command, cwd, env)
    except FileNotFoundError as exc:
        raise BootstrapError(
            f"Could not start command: {_format_command(command)}",
            command=command,
            remediation=remediation,
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise BootstrapError(
            f"Command exited with status {exc.returncode}.",
            command=command,
            remediation=remediation,
        ) from exc


def _run_subprocess(
    command: list[str],
    cwd: Path,
    env: dict[str, str] | None,
) -> None:
    """Execute a command with inherited stdio."""
    subprocess.run(command, check=True, cwd=cwd, env=env)


def _prompt_yes_no(
    input_fn: Callable[[str], str],
    prompt: str,
    *,
    default: bool,
) -> bool:
    """Prompt until the user enters a valid yes/no response."""
    while True:
        raw = input_fn(prompt).strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False


def _print_next_steps(stdout: TextIO) -> None:
    """Print the next commands a user can run after bootstrap."""
    activate_command = (
        r".venv\Scripts\activate" if os.name == "nt" else "source .venv/bin/activate"
    )
    print("", file=stdout)
    print("NeuroCore bootstrap is complete.", file=stdout)
    print("Next steps:", file=stdout)
    print(f"1. {activate_command}", file=stdout)
    print("2. set -a", file=stdout)
    print("3. source .env", file=stdout)
    print("4. set +a", file=stdout)
    print(
        '5. neurocore capture --request-json \'{"bucket":"recon","content":"initial '
        'recon note","content_format":"markdown","source_type":"note"}\'',
        file=stdout,
    )
    print(
        '6. neurocore query --request-json \'{"query_text":"recon",'
        '"allowed_buckets":["recon","findings"],'
        '"sensitivity_ceiling":"restricted"}\'',
        file=stdout,
    )


def _validate_namespace(namespace: str) -> None:
    """Validate a namespace value before writing it into local config."""
    if not NAMESPACE_PATTERN.match(namespace):
        raise BootstrapError(
            "Namespace must start with a lowercase letter or number and use only "
            "lowercase letters, numbers, underscores, or hyphens.",
            remediation="Choose a namespace like security-lab, h1-acme, or pt_client.",
        )


def _format_command(command: list[str]) -> str:
    """Render a shell-safe command preview."""
    return " ".join(shlex.quote(part) for part in command)


if __name__ == "__main__":
    raise SystemExit(main())
