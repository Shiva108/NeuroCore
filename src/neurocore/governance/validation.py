"""Repository governance validation utilities for NeuroCore."""

from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

ECOSYSTEM_CATEGORIES = (
    "extensions",
    "primitives",
    "recipes",
    "skills",
    "dashboards",
    "integrations",
    "schemas",
)
REQUIRED_FILES = (
    "README.md",
    "CONTRIBUTING.md",
    "docs/ai-assisted-setup.md",
    "docs/templates/setup-guide-template.md",
    "docs/reference-stack.md",
    "docs/hosted-stack.md",
)
REQUIRED_TEMPLATE_FILES = tuple(
    f"{category}/_template/{filename}"
    for category in ECOSYSTEM_CATEGORIES
    for filename in ("README.md", "metadata.json")
)
SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?im)^\s*(SECRET[_-]?KEY|API[_-]?KEY)\s*=\s*(.+)$"),
)
REQUIRED_GUIDANCE_PHRASES = (
    "docs-first planning phase",
    "There are no application source files yet",
    "No build, test, or local run commands are defined in this repository yet",
    "Until a runtime is selected",
    "not initialized as a Git repository yet",
)
GUIDANCE_FILES = (
    "AGENTS.md",
    "README.md",
    "CONTRIBUTING.md",
    "docs/ai-assisted-setup.md",
    "docs/setup.md",
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


def load_contribution_metadata_schema(root: Path) -> dict[str, object]:
    schema_path = root / ".github" / "contribution-metadata.schema.json"
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


def validate_contribution_metadata(
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

    expected_category = Path(source).parts[0]
    actual_category = metadata.get("category")
    if (
        expected_category in ECOSYSTEM_CATEGORIES
        and actual_category != expected_category
    ):
        errors.append(
            f"{source}: category must match parent folder ({expected_category})"
        )
    if (
        actual_category in {"extensions", "primitives"}
        and metadata.get("curation") != "curated"
    ):
        errors.append(f"{source}: curated categories must declare curation=curated")
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


def discover_contribution_metadata_files(root: Path) -> list[Path]:
    discovered: list[Path] = []
    for category in ECOSYSTEM_CATEGORIES:
        category_dir = root / category
        if not category_dir.exists():
            continue
        for path in category_dir.rglob("metadata.json"):
            if _should_ignore_path(path.relative_to(root)):
                continue
            discovered.append(path)
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


def find_stale_repo_guidance(
    root: Path, *, required_phrases: tuple[str, ...] = REQUIRED_GUIDANCE_PHRASES
) -> list[str]:
    findings: list[str] = []
    for relative_path in GUIDANCE_FILES:
        path = root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in required_phrases:
            if phrase in text:
                findings.append(
                    f"{relative_path}: stale guidance phrase detected: {phrase}"
                )
    return findings


def validate_repo_contract(root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_FILES + REQUIRED_TEMPLATE_FILES:
        if not (root / relative_path).exists():
            errors.append(f"Missing required file: {relative_path}")
    errors.extend(find_stale_repo_guidance(root))
    return errors


def validate_contribution_structure(root: Path, metadata_path: Path) -> list[str]:
    errors: list[str] = []
    parent = metadata_path.parent
    relative_parent = parent.relative_to(root)
    readme_path = parent / "README.md"
    if not readme_path.exists():
        errors.append(f"{relative_parent}: missing required README.md")

    category = relative_parent.parts[0]
    if category == "skills":
        if not any(
            (parent / filename).exists()
            for filename in ("SKILL.md", "skill.md", f"{parent.name}-skill.md")
        ):
            errors.append(f"{relative_parent}: skills must include a skill artifact")
    return errors


def main(root: str = ".") -> int:
    repo_root = Path(root)
    errors = validate_repo_contract(repo_root)
    schema = load_module_metadata_schema(repo_root)
    contribution_schema = load_contribution_metadata_schema(repo_root)

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

    for metadata_path in discover_contribution_metadata_files(repo_root):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{metadata_path}: invalid JSON ({exc.msg})")
            continue
        errors.extend(
            validate_contribution_metadata(
                metadata,
                schema=contribution_schema,
                source=str(metadata_path.relative_to(repo_root)),
            )
        )
        errors.extend(validate_contribution_structure(repo_root, metadata_path))

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
