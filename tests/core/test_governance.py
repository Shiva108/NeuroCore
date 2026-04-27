import json
from pathlib import Path

from neurocore.governance.validation import (
    ECOSYSTEM_CATEGORIES,
    REQUIRED_GUIDANCE_PHRASES,
    discover_contribution_metadata_files,
    discover_metadata_files,
    find_secret_like_values,
    find_stale_repo_guidance,
    load_contribution_metadata_schema,
    load_module_metadata_schema,
    validate_contribution_structure,
    validate_contribution_metadata,
    validate_module_metadata,
    validate_repo_contract,
)


def test_validate_module_metadata_reports_missing_required_fields():
    schema = load_module_metadata_schema(Path("."))
    errors = validate_module_metadata(
        {
            "name": "memory-query",
            "kind": "module",
        },
        schema=schema,
        source="memory-query/module-metadata.json",
    )

    assert any("memory-query/module-metadata.json" in error for error in errors)
    assert any("description" in error for error in errors)
    assert any("test_coverage" in error for error in errors)


def test_validate_module_metadata_reports_schema_type_errors():
    schema = load_module_metadata_schema(Path("."))
    errors = validate_module_metadata(
        {
            "name": "memory-query",
            "kind": "module",
            "description": "Query adapter and ranking support.",
            "owner": "neurocore",
            "status": "active",
            "interfaces": "library",
            "test_coverage": "pytest",
        },
        schema=schema,
        source="memory-query/module-metadata.json",
    )

    assert any("interfaces" in error for error in errors)


def test_find_secret_like_values_detects_obvious_secret_patterns():
    findings = find_secret_like_values(
        f"AWS_KEY={'AKIA' + 'IOSFODNN7EXAMPLE'}\n{'SECRET' + '_KEY'}=super-secret-value\n"
    )

    assert findings


def test_find_secret_like_values_ignores_placeholders_and_code_references():
    findings = find_secret_like_values(
        "API_KEY=\napi_key=config.consensus_api_key,\nSECRET_KEY=placeholder\n"
    )

    assert findings == []


def test_validate_repo_contract_requires_expected_docs(tmp_path: Path):
    (tmp_path / "README.md").write_text("# NeuroCore\n", encoding="utf-8")
    errors = validate_repo_contract(tmp_path)

    assert "Missing required file: CONTRIBUTING.md" in errors


def test_validate_repo_contract_requires_reference_stack_docs_and_templates(
    tmp_path: Path,
):
    for relative_path in (
        "README.md",
        "CONTRIBUTING.md",
        "docs/ai-assisted-setup.md",
        "docs/templates/setup-guide-template.md",
    ):
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("placeholder\n", encoding="utf-8")

    errors = validate_repo_contract(tmp_path)

    assert "Missing required file: docs/reference-stack.md" in errors
    assert "Missing required file: docs/hosted-stack.md" in errors
    assert "Missing required file: recipes/_template/README.md" in errors
    assert "Missing required file: skills/_template/metadata.json" in errors


def test_find_stale_repo_guidance_flags_docs_first_language(tmp_path: Path):
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text(
        (
            "# Repository Guidelines\n\n"
            "This repository is currently in a docs-first planning phase.\n"
            "There are no application source files yet.\n"
        ),
        encoding="utf-8",
    )

    findings = find_stale_repo_guidance(
        tmp_path,
        required_phrases=REQUIRED_GUIDANCE_PHRASES,
    )

    assert any("docs-first planning phase" in finding for finding in findings)


def test_validate_contribution_metadata_accepts_minimal_recipe_contract():
    schema = load_contribution_metadata_schema(Path("."))
    errors = validate_contribution_metadata(
        {
            "name": "Quick Capture Recipe",
            "category": "recipes",
            "description": "Capture notes with the NeuroCore CLI.",
            "owner": {"name": "NeuroCore"},
            "version": "1.0.0",
            "requires": {"neurocore": True, "tools": ["Python 3.11+"]},
            "tags": ["capture"],
            "difficulty": "beginner",
            "estimated_time": "10 minutes",
        },
        schema=schema,
        source="recipes/quick-capture/metadata.json",
    )

    assert errors == []


def test_validate_contribution_metadata_rejects_category_mismatch():
    schema = load_contribution_metadata_schema(Path("."))
    errors = validate_contribution_metadata(
        {
            "name": "Quick Capture Recipe",
            "category": "skills",
            "description": "Capture notes with the NeuroCore CLI.",
            "owner": {"name": "NeuroCore"},
            "version": "1.0.0",
            "requires": {"neurocore": True, "tools": ["Python 3.11+"]},
            "tags": ["capture"],
            "difficulty": "beginner",
            "estimated_time": "10 minutes",
        },
        schema=schema,
        source="recipes/quick-capture/metadata.json",
    )

    assert any("category must match parent folder" in error for error in errors)


def test_ecosystem_categories_match_expected_taxonomy():
    assert ECOSYSTEM_CATEGORIES == (
        "extensions",
        "primitives",
        "recipes",
        "skills",
        "dashboards",
        "integrations",
        "schemas",
    )


def test_repo_contribution_templates_and_examples_validate():
    root = Path(".")
    schema = load_contribution_metadata_schema(root)
    metadata_files = discover_contribution_metadata_files(root)

    assert root / "recipes" / "_template" / "metadata.json" in metadata_files
    assert root / "skills" / "_template" / "metadata.json" in metadata_files
    assert root / "integrations" / "_template" / "metadata.json" in metadata_files
    assert (
        root / "recipes" / "quickstart-memory-capture" / "metadata.json"
        in metadata_files
    )
    assert (
        root / "recipes" / "hosted-stack-quickstart" / "metadata.json"
        in metadata_files
    )
    assert (
        root / "recipes" / "slack-slash-flow-report" / "metadata.json"
        in metadata_files
    )
    assert (
        root / "recipes" / "discord-slash-flow-report" / "metadata.json"
        in metadata_files
    )
    assert (
        root / "recipes" / "security-memory-review-report" / "metadata.json"
        in metadata_files
    )
    assert (
        root / "recipes" / "ops-weekly-memory-report" / "metadata.json"
        in metadata_files
    )
    assert root / "skills" / "daily-memory-triage" / "metadata.json" in metadata_files
    assert root / "integrations" / "chat-capture" / "metadata.json" in metadata_files
    assert root / "integrations" / "slack-starter" / "metadata.json" in metadata_files
    assert root / "integrations" / "discord-starter" / "metadata.json" in metadata_files

    for metadata_path in metadata_files:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert (
            validate_contribution_metadata(
                metadata,
                schema=schema,
                source=str(metadata_path.relative_to(root)),
            )
            == []
        )
        assert validate_contribution_structure(root, metadata_path) == []


def test_discover_metadata_files_finds_repo_targets_and_ignores_other_json(
    tmp_path: Path,
):
    metadata_dir = tmp_path / "src" / "memory"
    metadata_dir.mkdir(parents=True)
    fixture_dir = tmp_path / "tests" / "fixtures" / "metadata"
    fixture_dir.mkdir(parents=True)
    (metadata_dir / "module-metadata.json").write_text("{}", encoding="utf-8")
    (fixture_dir / "sample-module.json").write_text("{}", encoding="utf-8")
    (tmp_path / "src" / "memory" / "other.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".git" / "ignored").mkdir(parents=True)
    (tmp_path / ".git" / "ignored" / "module-metadata.json").write_text(
        "{}", encoding="utf-8"
    )

    discovered = discover_metadata_files(tmp_path)

    assert metadata_dir / "module-metadata.json" in discovered
    assert fixture_dir / "sample-module.json" in discovered
    assert tmp_path / "src" / "memory" / "other.json" not in discovered


def test_validate_module_metadata_accepts_sample_fixture():
    root = Path(".")
    schema = load_module_metadata_schema(root)
    fixture_path = root / "tests" / "fixtures" / "metadata" / "sample-module.json"
    metadata = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert (
        validate_module_metadata(metadata, schema=schema, source=str(fixture_path))
        == []
    )
