"""Repository governance validation utilities for NeuroCore."""

from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

REQUIRED_FILES = (
    "README.md",
    "CONTRIBUTING.md",
    "docs/ai-assisted-setup.md",
    "docs/templates/setup-guide-template.md",
)
SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?im)^\s*(SECRET[_-]?KEY|API[_-]?KEY)\s*=\s*(.+)$"),
)
IGNORED_SCAN_PARTS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
}


def load_module_metadata_schema(root: Path) -> dict[str, object]:
    schema_path = root / ".github" / "module-metadata.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_module_metadata(
    metadata: dict[str, object],
    *,
    schema: dict[str, object],
    source: str,
) -> list[str]:
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(metadata), key=str):
        field = ".".join(str(part) for part in error.absolute_path)
        suffix = f" (field: {field})" if field else ""
        errors.append(f"{source}: {error.message}{suffix}")
    return errors


def discover_metadata_files(root: Path) -> list[Path]:
    discovered: set[Path] = set()
    for path in root.rglob("module-metadata.json"):
        if _should_ignore_path(path.relative_to(root)):
            continue
        discovered.add(path)

    fixture_dir = root / "tests" / "fixtures" / "metadata"
    if fixture_dir.exists():
        for path in fixture_dir.rglob("*.json"):
            if _should_ignore_path(path.relative_to(root)):
                continue
            discovered.add(path)

    return sorted(discovered)


def find_secret_like_values(text: str) -> list[str]:
    findings: list[str] = []
    for pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            if match.lastindex == 2:
                value = match.group(2).strip()
                if _looks_secret_assignment_value(value):
                    findings.append(match.group(0))
                continue
            findings.append(match.group(0))
    return findings


def validate_repo_contract(root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_FILES:
        if not (root / relative_path).exists():
            errors.append(f"Missing required file: {relative_path}")
    return errors


def main(root: str = ".") -> int:
    repo_root = Path(root)
    errors = validate_repo_contract(repo_root)
    schema = load_module_metadata_schema(repo_root)

    for metadata_path in discover_metadata_files(repo_root):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{metadata_path}: invalid JSON ({exc.msg})")
            continue
        errors.extend(
            validate_module_metadata(
                metadata,
                schema=schema,
                source=str(metadata_path.relative_to(repo_root)),
            )
        )

    findings: list[str] = []
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if _should_ignore_path(path.relative_to(repo_root)):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(
            f"{path.relative_to(repo_root)}: {value}"
            for value in find_secret_like_values(text)
        )

    if errors or findings:
        for error in errors:
            print(error)
        for finding in findings:
            print(f"Secret-like value detected: {finding}")
        return 1
    return 0


def _should_ignore_path(path: Path) -> bool:
    return any(part in IGNORED_SCAN_PARTS for part in path.parts)


def _looks_secret_assignment_value(value: str) -> bool:
    if not value:
        return False
    lowered = value.lower().strip("\"'")
    if lowered in {"", "none", "null"}:
        return False
    if lowered in {"changeme", "placeholder", "example", "test-key"}:
        return False
    if any(
        token in lowered for token in ("config.", "os.getenv", "getenv(", "{", "}", ",")
    ):
        return False
    return len(lowered) >= 12


if __name__ == "__main__":
    raise SystemExit(main())
