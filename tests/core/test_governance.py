import json
from pathlib import Path

from neurocore.governance.validation import (
    discover_metadata_files,
    find_secret_like_values,
    load_module_metadata_schema,
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
