import importlib.util
import io
import json
import os
from pathlib import Path

import pytest


def load_security_workflow_module():
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "security_workflow.py"
    spec = importlib.util.spec_from_file_location("security_workflow_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SECURITY_WORKFLOW = load_security_workflow_module()


def test_runtime_env_sets_bridge_defaults_when_env_file_is_missing(tmp_path: Path):
    env = SECURITY_WORKFLOW._runtime_env(tmp_path)

    assert env["NEUROCORE_ALLOWED_BUCKETS"] == ",".join(SECURITY_WORKFLOW.SECURITY_BUCKETS)
    assert env["NEUROCORE_DEFAULT_SENSITIVITY"] == "restricted"
    assert env["NEUROCORE_DEFAULT_NAMESPACE"] == "security-lab"
    assert env["PYTHONPATH"] == str(tmp_path / "src")


def test_capabilities_reports_missing_namespace_and_disabled_reporting(tmp_path: Path):
    env = {
        "NEUROCORE_ALLOWED_BUCKETS": ",".join(SECURITY_WORKFLOW.SECURITY_BUCKETS),
        "NEUROCORE_DEFAULT_SENSITIVITY": "restricted",
    }

    payload = SECURITY_WORKFLOW._capabilities_payload(tmp_path, env)

    assert payload["config_ready"] is False
    assert payload["query_ready"] is False
    assert payload["report_ready"] is False
    assert payload["semantic_ready"] is False
    assert payload["default_namespace_ready"] is False
    assert payload["consensus_report_ready"] is False
    assert payload["report_provider_mode"] == "disabled"
    assert payload["resolved_python"] is None
    assert "default_namespace" in payload["issues_by_surface"]
    assert any("NEUROCORE_DEFAULT_NAMESPACE" in issue for issue in payload["issues"])


def test_capabilities_reports_ready_config_and_consensus(tmp_path: Path):
    (tmp_path / ".env").write_text("NEUROCORE_DEFAULT_NAMESPACE=security-lab\n", encoding="utf-8")
    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True, exist_ok=True)
    python_path.write_text("", encoding="utf-8")
    env = {
        "NEUROCORE_DEFAULT_NAMESPACE": "security-lab",
        "NEUROCORE_ALLOWED_BUCKETS": ",".join(SECURITY_WORKFLOW.SECURITY_BUCKETS),
        "NEUROCORE_DEFAULT_SENSITIVITY": "restricted",
        "NEUROCORE_SEMANTIC_BACKEND": "none",
        "NEUROCORE_ENABLE_MULTI_MODEL_CONSENSUS": "true",
        "NEUROCORE_CONSENSUS_PROVIDER": "openai_compatible",
        "NEUROCORE_CONSENSUS_MODEL_NAMES": "model-a,model-b",
        "NEUROCORE_CONSENSUS_BASE_URL": "https://example.invalid/v1",
        "NEUROCORE_CONSENSUS_API_KEY": "test-key",
    }

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(SECURITY_WORKFLOW, "_check_reporter_health", lambda config: (True, None))
    try:
        payload = SECURITY_WORKFLOW._capabilities_payload(tmp_path, env)
    finally:
        monkeypatch.undo()

    assert payload["config_ready"] is True
    assert payload["query_ready"] is True
    assert payload["briefing_ready"] is True
    assert payload["report_ready"] is True
    assert payload["semantic_ready"] is True
    assert payload["default_namespace_ready"] is True
    assert payload["consensus_report_ready"] is True
    assert payload["report_provider_mode"] == "external_openai_compatible"
    assert payload["resolved_python"] == str(python_path.absolute())
    assert payload["issues"] == []


def test_capabilities_reports_mock_local_provider_mode(tmp_path: Path):
    (tmp_path / ".env").write_text("NEUROCORE_DEFAULT_NAMESPACE=security-lab\n", encoding="utf-8")
    env = {
        "NEUROCORE_DEFAULT_NAMESPACE": "security-lab",
        "NEUROCORE_ALLOWED_BUCKETS": ",".join(SECURITY_WORKFLOW.SECURITY_BUCKETS),
        "NEUROCORE_DEFAULT_SENSITIVITY": "restricted",
        "NEUROCORE_SEMANTIC_BACKEND": "none",
        "NEUROCORE_ENABLE_MULTI_MODEL_CONSENSUS": "true",
        "NEUROCORE_CONSENSUS_PROVIDER": "openai_compatible",
        "NEUROCORE_CONSENSUS_MODEL_NAMES": "model-a,model-b",
        "NEUROCORE_CONSENSUS_BASE_URL": SECURITY_WORKFLOW.LOCAL_CONSENSUS_BASE_URL,
        "NEUROCORE_CONSENSUS_API_KEY": "local-dev-key",
    }

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(SECURITY_WORKFLOW, "_check_reporter_health", lambda config: (True, None))
    try:
        payload = SECURITY_WORKFLOW._capabilities_payload(tmp_path, env)
    finally:
        monkeypatch.undo()

    assert payload["report_ready"] is True
    assert payload["briefing_ready"] is True
    assert payload["report_provider_mode"] == "mock_local"


def test_capabilities_marks_report_unready_when_local_mock_health_fails(tmp_path: Path):
    (tmp_path / ".env").write_text("NEUROCORE_DEFAULT_NAMESPACE=security-lab\n", encoding="utf-8")
    env = {
        "NEUROCORE_DEFAULT_NAMESPACE": "security-lab",
        "NEUROCORE_ALLOWED_BUCKETS": ",".join(SECURITY_WORKFLOW.SECURITY_BUCKETS),
        "NEUROCORE_DEFAULT_SENSITIVITY": "restricted",
        "NEUROCORE_SEMANTIC_BACKEND": "none",
        "NEUROCORE_ENABLE_MULTI_MODEL_CONSENSUS": "true",
        "NEUROCORE_CONSENSUS_PROVIDER": "openai_compatible",
        "NEUROCORE_CONSENSUS_MODEL_NAMES": "model-a,model-b",
        "NEUROCORE_CONSENSUS_BASE_URL": SECURITY_WORKFLOW.LOCAL_CONSENSUS_BASE_URL,
        "NEUROCORE_CONSENSUS_API_KEY": "local-dev-key",
    }
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        SECURITY_WORKFLOW,
        "_check_reporter_health",
        lambda config: (False, "mock provider health check failed"),
    )
    try:
        payload = SECURITY_WORKFLOW._capabilities_payload(tmp_path, env)
    finally:
        monkeypatch.undo()

    assert payload["query_ready"] is True
    assert payload["briefing_ready"] is True
    assert payload["report_ready"] is False
    assert payload["issues_by_surface"]["report"] == ["mock provider health check failed"]


def test_capabilities_bootstraps_local_mock_and_rechecks_health(tmp_path: Path):
    (tmp_path / ".env").write_text("NEUROCORE_DEFAULT_NAMESPACE=security-lab\n", encoding="utf-8")
    env = {
        "NEUROCORE_DEFAULT_NAMESPACE": "security-lab",
        "NEUROCORE_ALLOWED_BUCKETS": ",".join(SECURITY_WORKFLOW.SECURITY_BUCKETS),
        "NEUROCORE_DEFAULT_SENSITIVITY": "restricted",
        "NEUROCORE_SEMANTIC_BACKEND": "none",
        "NEUROCORE_ENABLE_MULTI_MODEL_CONSENSUS": "true",
        "NEUROCORE_CONSENSUS_PROVIDER": "openai_compatible",
        "NEUROCORE_CONSENSUS_MODEL_NAMES": "model-a,model-b",
        "NEUROCORE_CONSENSUS_BASE_URL": SECURITY_WORKFLOW.LOCAL_CONSENSUS_BASE_URL,
        "NEUROCORE_CONSENSUS_API_KEY": "local-dev-key",
    }
    health_checks = iter(
        [
            (False, "mock provider health check failed"),
            (True, None),
        ]
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        SECURITY_WORKFLOW,
        "_check_reporter_health",
        lambda config: next(health_checks),
    )
    monkeypatch.setattr(
        SECURITY_WORKFLOW,
        "_bootstrap_reporter",
        lambda repo_root, env, config: {
            "mode": "mock_local",
            "started": True,
            "healthy": True,
            "base_url": SECURITY_WORKFLOW.LOCAL_CONSENSUS_BASE_URL,
        },
    )
    try:
        payload = SECURITY_WORKFLOW._capabilities_payload(tmp_path, env)
    finally:
        monkeypatch.undo()

    assert payload["report_ready"] is True
    assert payload["report_bootstrap_attempted"] is True
    assert payload["report_bootstrap_started"] is True


def test_check_reporter_health_uses_root_health_endpoint_for_local_mock(monkeypatch: pytest.MonkeyPatch):
    class DummyConfig:
        consensus_base_url = SECURITY_WORKFLOW.LOCAL_CONSENSUS_BASE_URL
        consensus_api_key = "local-dev-key"

    requested_urls: list[str] = []

    class DummyResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout: float = 0.0):
        requested_urls.append(request.full_url)
        return DummyResponse()

    monkeypatch.setattr(SECURITY_WORKFLOW.urllib_request, "urlopen", fake_urlopen)

    ready, issue = SECURITY_WORKFLOW._check_reporter_health(DummyConfig())

    assert ready is True
    assert issue is None
    assert requested_urls == ["http://127.0.0.1:8787/health"]


def test_is_local_mock_base_url_accepts_ephemeral_local_ports():
    assert SECURITY_WORKFLOW._is_local_mock_base_url("http://127.0.0.1:39321/v1") is True
    assert SECURITY_WORKFLOW._is_local_mock_base_url("http://localhost:8080/v1") is True
    assert SECURITY_WORKFLOW._is_local_mock_base_url("https://api.example.test/v1") is False


def test_capabilities_marks_config_unready_when_semantic_backend_dependency_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    (tmp_path / ".env").write_text("NEUROCORE_DEFAULT_NAMESPACE=security-lab\n", encoding="utf-8")
    env = {
        "NEUROCORE_DEFAULT_NAMESPACE": "security-lab",
        "NEUROCORE_ALLOWED_BUCKETS": ",".join(SECURITY_WORKFLOW.SECURITY_BUCKETS),
        "NEUROCORE_DEFAULT_SENSITIVITY": "restricted",
        "NEUROCORE_SEMANTIC_BACKEND": "sentence-transformers",
    }
    monkeypatch.setattr(
        SECURITY_WORKFLOW,
        "sentence_transformers_status",
        lambda: ("unavailable", "sentence-transformers missing"),
    )

    payload = SECURITY_WORKFLOW._capabilities_payload(tmp_path, env)

    assert payload["config_ready"] is False
    assert payload["query_ready"] is False
    assert payload["briefing_ready"] is False
    assert payload["consensus_report_ready"] is False
    assert payload["report_ready"] is False
    assert payload["semantic_ready"] is False
    assert payload["issues_by_surface"]["semantic"] == ["sentence-transformers missing"]
    assert "sentence-transformers missing" in payload["issues"]


def test_capabilities_query_ready_without_report_when_consensus_disabled(tmp_path: Path):
    (tmp_path / ".env").write_text("NEUROCORE_DEFAULT_NAMESPACE=security-lab\n", encoding="utf-8")
    env = {
        "NEUROCORE_DEFAULT_NAMESPACE": "security-lab",
        "NEUROCORE_ALLOWED_BUCKETS": ",".join(SECURITY_WORKFLOW.SECURITY_BUCKETS),
        "NEUROCORE_DEFAULT_SENSITIVITY": "restricted",
        "NEUROCORE_SEMANTIC_BACKEND": "none",
        "NEUROCORE_ENABLE_MULTI_MODEL_CONSENSUS": "false",
    }

    payload = SECURITY_WORKFLOW._capabilities_payload(tmp_path, env)

    assert payload["config_ready"] is True
    assert payload["query_ready"] is True
    assert payload["briefing_ready"] is True
    assert payload["semantic_ready"] is True
    assert payload["report_ready"] is False
    assert payload["consensus_report_ready"] is False
    assert payload["report_provider_mode"] == "disabled"
    assert payload["issues_by_surface"]["report"] == ["Consensus reporting disabled"]


def test_capabilities_query_ready_without_report_when_consensus_key_missing(tmp_path: Path):
    (tmp_path / ".env").write_text("NEUROCORE_DEFAULT_NAMESPACE=security-lab\n", encoding="utf-8")
    env = {
        "NEUROCORE_DEFAULT_NAMESPACE": "security-lab",
        "NEUROCORE_ALLOWED_BUCKETS": ",".join(SECURITY_WORKFLOW.SECURITY_BUCKETS),
        "NEUROCORE_DEFAULT_SENSITIVITY": "restricted",
        "NEUROCORE_SEMANTIC_BACKEND": "none",
        "NEUROCORE_ENABLE_MULTI_MODEL_CONSENSUS": "true",
        "NEUROCORE_CONSENSUS_PROVIDER": "openai_compatible",
        "NEUROCORE_CONSENSUS_MODEL_NAMES": "model-a,model-b",
        "NEUROCORE_CONSENSUS_BASE_URL": "https://example.invalid/v1",
    }

    payload = SECURITY_WORKFLOW._capabilities_payload(tmp_path, env)

    assert payload["query_ready"] is True
    assert payload["briefing_ready"] is True
    assert payload["report_ready"] is False
    assert payload["consensus_report_ready"] is False
    assert payload["report_provider_mode"] == "external_openai_compatible"
    assert payload["issues_by_surface"]["report"] == [
        "Consensus reporting requires a consensus API key"
    ]


def test_resolve_repo_python_prefers_override_then_unix_then_windows(tmp_path: Path):
    override = tmp_path / "python-custom"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text("", encoding="utf-8")

    assert SECURITY_WORKFLOW._resolve_repo_python(
        tmp_path, {"NEUROCORE_PYTHON_EXECUTABLE": str(override)}
    ) == override

    unix_python = tmp_path / ".venv" / "bin" / "python"
    unix_python.parent.mkdir(parents=True, exist_ok=True)
    unix_python.write_text("", encoding="utf-8")
    assert SECURITY_WORKFLOW._resolve_repo_python(tmp_path, {}) == unix_python

    unix_python.unlink()
    windows_python = tmp_path / ".venv" / "Scripts" / "python.exe"
    windows_python.parent.mkdir(parents=True, exist_ok=True)
    windows_python.write_text("", encoding="utf-8")
    assert SECURITY_WORKFLOW._resolve_repo_python(tmp_path, {}) == windows_python


def test_maybe_reexec_into_repo_runtime_uses_repo_python(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True, exist_ok=True)
    python_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(SECURITY_WORKFLOW.sys, "prefix", "/usr")
    called: dict[str, object] = {}

    def fake_execve(binary, argv, env):
        called["binary"] = binary
        called["argv"] = argv
        called["env"] = env
        raise SystemExit(0)

    monkeypatch.setattr(SECURITY_WORKFLOW.os, "execve", fake_execve)

    with pytest.raises(SystemExit):
        SECURITY_WORKFLOW._maybe_reexec_into_repo_runtime(["capabilities"], tmp_path)

    expected_script = str(Path(SECURITY_WORKFLOW.__file__).resolve())
    assert called["binary"] == str(python_path.absolute())
    assert called["argv"] == [str(python_path.absolute()), expected_script, "capabilities"]
    assert called["env"]["NEUROCORE_SKIP_RUNTIME_REEXEC"] == "1"


def test_run_neurocore_uses_resolved_python_and_formats_json_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True, exist_ok=True)
    python_path.write_text("", encoding="utf-8")

    def fake_run(command, cwd, env, text, capture_output):
        assert command[:4] == [
            str(python_path),
            "-m",
            "neurocore.adapters.cli",
            "query",
        ]
        return type(
            "Completed",
            (),
            {"returncode": 0, "stdout": '{"ok": true}', "stderr": ""},
        )()

    monkeypatch.setattr(SECURITY_WORKFLOW.subprocess, "run", fake_run)
    stdout = io.StringIO()
    monkeypatch.setattr(SECURITY_WORKFLOW.sys, "stdout", stdout)

    exit_code = SECURITY_WORKFLOW._run_neurocore(
        tmp_path,
        {"NEUROCORE_DEFAULT_NAMESPACE": "security-lab"},
        "query",
        {"query_text": "hello"},
    )

    assert exit_code == 0
    assert json.loads(stdout.getvalue())["ok"] is True


def test_main_capabilities_prints_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    stdout = io.StringIO()
    monkeypatch.setattr(SECURITY_WORKFLOW.sys, "stdout", stdout)
    monkeypatch.setattr(SECURITY_WORKFLOW.Path, "resolve", lambda self: tmp_path)
    monkeypatch.setattr(SECURITY_WORKFLOW, "_maybe_reexec_into_repo_runtime", lambda argv, repo_root: None)

    exit_code = SECURITY_WORKFLOW.main(["capabilities"])

    assert exit_code == 0
    payload = json.loads(stdout.getvalue())
    assert "config_ready" in payload
    assert "report_provider_mode" in payload


def test_main_forwards_capture_hackingagent_query_and_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    calls: list[tuple[object, dict[str, object]]] = []

    def fake_run_neurocore(repo_root, env, command, request):
        calls.append((command, request))
        return 0

    monkeypatch.setattr(SECURITY_WORKFLOW, "_run_neurocore", fake_run_neurocore)
    monkeypatch.setattr(SECURITY_WORKFLOW.Path, "resolve", lambda self: tmp_path)
    monkeypatch.setattr(SECURITY_WORKFLOW, "_maybe_reexec_into_repo_runtime", lambda argv, repo_root: None)
    monkeypatch.setattr(
        SECURITY_WORKFLOW, "_read_text_file", lambda path, description: "artifact body"
    )

    artifact = tmp_path / "artifact.md"
    artifact.write_text("artifact body", encoding="utf-8")

    assert (
        SECURITY_WORKFLOW.main(
            [
                "capture-hackingagent",
                "--namespace",
                "pt-acme",
                "--artifact-type",
                "report-summary",
                "--target",
                "acme",
                str(artifact),
            ]
        )
        == 0
    )
    assert SECURITY_WORKFLOW.main(["query", "--namespace", "pt-acme", "acme findings"]) == 0
    assert (
        SECURITY_WORKFLOW.main(
            [
                "report",
                "--namespace",
                "pt-acme",
                "--objective",
                "Generate report",
                "acme findings",
            ]
        )
        == 0
    )

    capture_command, capture_request = calls[0]
    query_command, query_request = calls[1]
    report_command, report_request = calls[2]

    assert capture_command == "capture"
    assert capture_request["namespace"] == "pt-acme"
    assert capture_request["metadata"]["artifact_type"] == "report-summary"
    assert query_command == "query"
    assert query_request["namespace"] == "pt-acme"
    assert report_command == ["report", "consensus"]
    assert report_request["query_request"]["namespace"] == "pt-acme"


def test_print_readiness_summary_reports_missing_report_prereqs(tmp_path: Path):
    stdout = io.StringIO()
    env = {
        "NEUROCORE_DEFAULT_NAMESPACE": "security-lab",
        "NEUROCORE_ALLOWED_BUCKETS": ",".join(SECURITY_WORKFLOW.SECURITY_BUCKETS),
        "NEUROCORE_DEFAULT_SENSITIVITY": "restricted",
        "NEUROCORE_SEMANTIC_BACKEND": "none",
    }

    SECURITY_WORKFLOW.print_readiness_summary(repo_root=tmp_path, env=env, stdout=stdout)

    text = stdout.getvalue()
    assert "semantic=ready" in text
    assert "query=ready" in text
    assert "report=not ready" in text
    assert "Report prerequisites still missing" in text
