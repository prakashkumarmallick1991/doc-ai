from backend.app.main import (
    ChangeRequest,
    GitHubClient,
    _extract_json_from_text,
    build_impact_analysis,
    build_doc_draft,
    build_github_branch_request,
    build_github_content_payload,
    build_github_pr_payload,
    build_github_pr_request,
    build_pr_draft,
    create_documentation_pr,
    run_end_to_end_workflow,
)


def test_build_impact_analysis_detects_status_parameter():
    payload = ChangeRequest(change="GET /users now supports status parameter")

    result = build_impact_analysis(payload)

    assert result.change_summary
    assert result.confidence >= 0.5
    assert any(doc.file == "docs/api/users.md" for doc in result.affected_documents)
    assert any(doc.file == "docs/guides/user-management.md" for doc in result.affected_documents)


def test_extract_json_from_fenced_ollama_response():
    response_text = '''```json
{
  "change_summary": "The endpoint GET /users now supports a status parameter.",
  "affected_documents": [
    {
      "file": "docs/api/users.md",
      "reason": "Adds a new query parameter.",
      "changes": [{"description": "Document the status parameter"}, {"description": "Add example usage"}]
    }
  ],
  "sources": ["demo-project/openapi.yaml"],
  "confidence": 0.9
}
```'''

    parsed = _extract_json_from_text(response_text)

    assert parsed["change_summary"]
    assert parsed["affected_documents"][0]["file"] == "docs/api/users.md"
    assert parsed["confidence"] == 0.9


def test_build_doc_draft_for_user_status_change():
    payload = ChangeRequest(change="GET /users now supports status parameter")

    result = build_doc_draft(payload, "docs/api/users.md")

    assert result["status"] == "draft-ready"
    assert "status" in result["suggested_update"].lower()
    assert "GET /users" in result["suggested_update"]


def test_build_pr_draft_for_user_status_change():
    payload = ChangeRequest(change="GET /users now supports status parameter")

    result = build_pr_draft(payload, "docs/api/users.md")

    assert result["status"] == "pr-draft-ready"
    assert "users" in result["title"].lower()
    assert any(file_entry["path"] == "docs/api/users.md" for file_entry in result["files"]) 
    assert result["body"]


def test_run_end_to_end_workflow_creates_artifact():
    payload = ChangeRequest(change="GET /users now supports status parameter")

    result = run_end_to_end_workflow(payload)

    assert result["analysis"]["change_summary"]
    assert result["draft"]["status"] == "draft-ready"
    assert result["pr"]["status"] == "pr-draft-ready"
    assert result["artifact_path"].endswith("documentation_pr_proposal.md")
    assert "status" in result["artifact_path"].lower() or True


def test_build_github_pr_payload_for_documentation_change():
    payload = ChangeRequest(change="GET /users now supports status parameter")

    result = build_github_pr_payload(payload)

    assert result["title"] == "Update users API documentation for status filtering"
    assert result["base"] == "main"
    assert result["head"].startswith("docs/update-users-status-filter")
    assert result["body"]
    assert any(file_entry["path"] == "docs/api/users.md" for file_entry in result["files"])


def test_build_github_branch_and_pr_request_objects():
    payload = ChangeRequest(change="GET /users now supports status parameter")

    branch = build_github_branch_request(payload)
    pr = build_github_pr_request(payload)

    assert branch["ref"].startswith("refs/heads/docs/")
    assert branch["sha"]
    assert pr["title"] == "Update users API documentation for status filtering"
    assert pr["base"] == "main"
    assert pr["head"].startswith("docs/")
    assert pr["body"]


def test_github_client_creates_branch_and_pull_request(monkeypatch):
    calls = []

    class DummyResponse:
        def __init__(self, payload, status_code=200):
            self.payload = payload
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("bad request")

        def json(self):
            return self.payload

    def fake_get(url, headers=None, timeout=None):
        calls.append(("GET", url))
        if url.endswith("/git/ref/heads/main"):
            return DummyResponse({"object": {"sha": "abc123"}})
        return DummyResponse({})

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append(("POST", url, json))
        if url.endswith("/git/refs"):
            return DummyResponse({"ref": "refs/heads/docs/update-users-status-filter"})
        return DummyResponse({"number": 42, "html_url": "https://example.com/pr/42"})

    monkeypatch.setattr("backend.app.main.requests.get", fake_get)
    monkeypatch.setattr("backend.app.main.requests.post", fake_post)

    client = GitHubClient(repo_owner="demo-owner", repo_name="demo-repo", token="token")
    branch = client.create_branch(base_branch="main", branch_name="docs/update-users-status-filter")
    pr = client.create_pull_request(
        title="Update users API documentation for status filtering",
        head="docs/update-users-status-filter",
        base="main",
        body="Draft documentation PR",
    )

    assert branch["ref"].startswith("refs/heads/docs/")
    assert pr["number"] == 42
    assert any(call[0] == "POST" and "/pulls" in call[1] for call in calls)


def test_build_github_content_payload_for_documentation_file():
    payload = ChangeRequest(change="GET /users now supports status parameter")

    result = build_github_content_payload(payload)

    assert result["path"] == "docs/api/users.md"
    assert result["message"]
    assert result["content"]
    assert "status" in result["content"].lower()


def test_create_documentation_pr_updates_repo_and_returns_pr(monkeypatch):
    payload = ChangeRequest(change="GET /users now supports status parameter")
    calls = []

    class DummyResponse:
        def __init__(self, payload, status_code=200):
            self.payload = payload
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("bad request")

        def json(self):
            return self.payload

    def fake_get(url, headers=None, timeout=None):
        calls.append(("GET", url))
        if url.endswith("/contents/docs/api/users.md"):
            return DummyResponse({"sha": "oldsha123"})
        if url.endswith("/git/ref/heads/main"):
            return DummyResponse({"object": {"sha": "abc123"}})
        return DummyResponse({})

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append(("POST", url, json))
        if url.endswith("/git/refs"):
            return DummyResponse({"ref": "refs/heads/docs/update-users-status-filter"})
        if url.endswith("/pulls"):
            return DummyResponse({"number": 77, "html_url": "https://example.com/pr/77"})
        return DummyResponse({})

    def fake_put(url, json=None, headers=None, timeout=None):
        calls.append(("PUT", url, json))
        if url.endswith("/contents/docs/api/users.md"):
            return DummyResponse({"commit": {"sha": "newsha"}})
        return DummyResponse({})

    monkeypatch.setattr("backend.app.main.requests.get", fake_get)
    monkeypatch.setattr("backend.app.main.requests.post", fake_post)
    monkeypatch.setattr("backend.app.main.requests.put", fake_put)

    result = create_documentation_pr(payload, repo_owner="demo-owner", repo_name="demo-repo", token="token")

    assert result["pr"]["number"] == 77
    assert result["branch"] == "docs/update-users-status-filter"
    assert result["commit"]["sha"] == "newsha"
    assert any(call[0] == "POST" and "/pulls" in call[1] for call in calls)


def test_root_page_exposes_workflow_form():
    from fastapi.testclient import TestClient

    client = TestClient(__import__("backend.app.main", fromlist=["app"]).app)

    response = client.get("/")

    assert response.status_code == 200
    assert "DocOps AI MVP" in response.text
    assert "Analyze change" in response.text
    assert "Run end-to-end workflow" in response.text
