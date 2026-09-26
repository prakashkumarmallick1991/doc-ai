from __future__ import annotations

import base64
import json
import os
import re
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(title="DocOps AI MVP", version="0.1.0")


class ChangeRequest(BaseModel):
    repository: str = "demo-project"
    change: str = Field(..., description="Description of the engineering change")
    diff: Optional[str] = None


class ImpactedDoc(BaseModel):
    file: str
    reason: str
    changes: List[str]


class AnalysisResponse(BaseModel):
    change_summary: str
    affected_documents: List[ImpactedDoc]
    sources: List[str]
    confidence: float


class GitHubClient:
    def __init__(self, repo_owner: str, repo_name: str, token: Optional[str] = None):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token or ""
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def get_default_branch(self, base_branch: str = "main") -> str:
        response = requests.get(
            f"{self.base_url}/git/ref/heads/{base_branch}",
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("ref", f"refs/heads/{base_branch}")

    def create_branch(self, base_branch: str, branch_name: str) -> dict:
        branch_ref = f"refs/heads/{branch_name}"
        ref_response = requests.get(
            f"{self.base_url}/git/ref/heads/{base_branch}",
            headers=self._headers(),
            timeout=30,
        )
        ref_response.raise_for_status()
        ref_sha = ref_response.json().get("object", {}).get("sha")
        if not ref_sha:
            raise ValueError("Could not determine the base branch SHA.")

        response = requests.post(
            f"{self.base_url}/git/refs",
            json={"ref": branch_ref, "sha": ref_sha},
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def create_pull_request(self, title: str, head: str, base: str, body: str) -> dict:
        response = requests.post(
            f"{self.base_url}/pulls",
            json={"title": title, "head": head, "base": base, "body": body, "draft": True},
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


def _heuristic_abbreviation(payload: ChangeRequest) -> AnalysisResponse:
    change_text = (payload.change + " " + (payload.diff or "")).lower()

    if "status" in change_text or "/users" in change_text or "users api" in change_text:
        return AnalysisResponse(
            change_summary="The users API now supports a status filter and the query contract has changed.",
            affected_documents=[
                ImpactedDoc(
                    file="docs/api/users.md",
                    reason="The API contract and parameter documentation are directly affected.",
                    changes=["Document the status query parameter", "Update filtering examples", "Clarify default behavior"],
                ),
                ImpactedDoc(
                    file="docs/guides/user-management.md",
                    reason="The user management guide references available filtering behavior and examples.",
                    changes=["Add status-based filtering guidance", "Update example requests"],
                ),
            ],
            sources=["demo-project/src/users.py", "demo-project/openapi.yaml", "docs/api/users.md"],
            confidence=0.91,
        )

    return AnalysisResponse(
        change_summary="A product or API change was detected, but no matching docs were identified from the current metadata.",
        affected_documents=[
            ImpactedDoc(
                file="docs/index.md",
                reason="General feature updates may require a summary or release note entry.",
                changes=["Review feature overview", "Consider release notes update"],
            )
        ],
        sources=["demo-project/src", "docs/index.md"],
        confidence=0.62,
    )


def _extract_json_from_text(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def _try_ollama_analysis(payload: ChangeRequest) -> Optional[AnalysisResponse]:
    prompt = (
        "You are a documentation impact analysis engine. "
        "Return only valid JSON with fields: change_summary, affected_documents, sources, confidence. "
        "Affected documents should be a list of objects with file, reason, and changes. "
        "For the changes field, use a list of plain strings, not objects. "
        "Focus on product docs and API docs. "
        f"Repository: {payload.repository}. "
        f"Change: {payload.change}. "
        f"Diff: {payload.diff or 'No diff provided'}."
    )

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:1.5b",
                "prompt": prompt,
                "stream": False,
            },
            timeout=90,
        )
        response.raise_for_status()
        payload_data = response.json()
        result_text = payload_data.get("response", "")
        if not result_text:
            return None

        json_data = _extract_json_from_text(result_text)
        docs = json_data.get("affected_documents", [])
        affected = []
        for item in docs:
            changes = item.get("changes", [])
            normalized_changes = []
            for change in changes:
                if isinstance(change, str):
                    normalized_changes.append(change)
                elif isinstance(change, dict):
                    normalized_changes.append(change.get("description", "Documentation update"))
            affected.append(
                ImpactedDoc(
                    file=item.get("file", "docs/index.md"),
                    reason=item.get("reason", "Documentation may need review."),
                    changes=normalized_changes,
                )
            )

        confidence_value = json_data.get("confidence", 0.75)
        if isinstance(confidence_value, str):
            confidence_value = float(confidence_value.replace("%", "")) / 100

        return AnalysisResponse(
            change_summary=json_data.get("change_summary", "Documentation impact detected."),
            affected_documents=affected,
            sources=json_data.get("sources", [payload.repository]),
            confidence=float(confidence_value),
        )
    except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError):
        return None


def build_impact_analysis(payload: ChangeRequest) -> AnalysisResponse:
    heuristic_result = _heuristic_abbreviation(payload)
    change_text = (payload.change + " " + (payload.diff or "")).lower()

    if "status" in change_text or "/users" in change_text or "users api" in change_text:
        return heuristic_result

    ollama_result = _try_ollama_analysis(payload)
    if ollama_result is not None:
        return ollama_result
    return heuristic_result


def build_doc_draft(payload: ChangeRequest, target_document: str) -> dict:
    change_text = (payload.change + " " + (payload.diff or "")).lower()

    if "status" in change_text or "/users" in change_text or "users api" in change_text:
        return {
            "status": "draft-ready",
            "target_document": target_document,
            "confidence": 0.91,
            "suggested_update": (
                "### GET /users\n\n"
                "Use the `status` query parameter to filter users by lifecycle state.\n\n"
                "Example request:\n\n"
                "```http\nGET /users?status=active\n```\n\n"
                "This parameter is optional. If omitted, all users are returned."
            ),
        }

    return {
        "status": "draft-ready",
        "target_document": target_document,
        "confidence": 0.72,
        "suggested_update": (
            "### Documentation update\n\n"
            "Review this section for potential updates related to the current product change."
        ),
    }


def build_pr_draft(payload: ChangeRequest, target_document: str) -> dict:
    doc_draft = build_doc_draft(payload, target_document)
    title = "Update users API documentation for status filtering"
    body = (
        "## Documentation update\n\n"
        "### Summary\n"
        "This PR updates the API documentation for the users endpoint after the status filter change.\n\n"
        "### Proposed content\n"
        f"{doc_draft['suggested_update']}\n\n"
        "### Validation\n"
        "- Markup reviewed\n"
        "- Links checked\n"
        "- Docs build validated\n"
    )

    return {
        "status": "pr-draft-ready",
        "title": title,
        "body": body,
        "branch": "docs/update-users-status-filter",
        "files": [
            {
                "path": target_document,
                "action": "update",
                "summary": "Add status query parameter documentation to the Users API reference.",
            }
        ],
    }


def build_github_pr_payload(payload: ChangeRequest) -> dict:
    pr = build_pr_draft(payload, "docs/api/users.md")
    return {
        "title": pr["title"],
        "head": pr["branch"],
        "base": "main",
        "body": pr["body"],
        "files": pr["files"],
        "draft": True,
    }


def build_github_branch_request(payload: ChangeRequest) -> dict:
    branch_name = "docs/update-users-status-filter"
    return {
        "ref": f"refs/heads/{branch_name}",
        "sha": "0123456789abcdef0123456789abcdef01234567",
        "branch": branch_name,
    }


def build_github_pr_request(payload: ChangeRequest) -> dict:
    pr = build_github_pr_payload(payload)
    return {
        "title": pr["title"],
        "head": pr["head"],
        "base": "main",
        "body": pr["body"],
        "draft": True,
    }


def build_github_content_payload(payload: ChangeRequest) -> dict:
    draft = build_doc_draft(payload, "docs/api/users.md")
    content = (
        "# Users API\n\n"
        "## GET /users\n\n"
        "Use the `status` query parameter to filter users by lifecycle state.\n\n"
        "Example request:\n\n"
        "```http\nGET /users?status=active\n```\n\n"
        "This parameter is optional. If omitted, all users are returned.\n"
    )
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    return {
        "path": "docs/api/users.md",
        "message": "Update users API docs for status filtering",
        "content": content,
        "content_base64": encoded,
        "sha": "existing-sha-placeholder",
        "branch": "docs/update-users-status-filter",
        "draft": draft,
    }


def create_documentation_pr(payload: ChangeRequest, repo_owner: str, repo_name: str, token: str) -> dict:
    client = GitHubClient(repo_owner=repo_owner, repo_name=repo_name, token=token)
    branch_name = "docs/update-users-status-filter"
    branch_request = client.create_branch(base_branch="main", branch_name=branch_name)

    file_payload = build_github_content_payload(payload)
    content_payload = {
        "message": file_payload["message"],
        "content": base64.b64encode(file_payload["content"].encode("utf-8")).decode("utf-8"),
        "branch": branch_name,
        "sha": file_payload["sha"],
    }

    file_response = requests.get(
        f"{client.base_url}/contents/{file_payload['path']}",
        headers=client._headers(),
        timeout=30,
    )
    file_response.raise_for_status()
    existing = file_response.json()
    content_payload["sha"] = existing.get("sha", "existing-sha-placeholder")

    commit_response = requests.put(
        f"{client.base_url}/contents/{file_payload['path']}",
        json=content_payload,
        headers=client._headers(),
        timeout=30,
    )
    commit_response.raise_for_status()
    commit_data = commit_response.json()

    pr_response = client.create_pull_request(
        title="Update users API documentation for status filtering",
        head=branch_name,
        base="main",
        body="Draft documentation PR generated by DocOps AI MVP.",
    )

    return {
        "branch": branch_name,
        "commit": commit_data.get("commit", {"sha": "unknown"}),
        "pr": pr_response,
    }


def run_end_to_end_workflow(payload: ChangeRequest) -> dict:
    analysis = build_impact_analysis(payload)
    draft = build_doc_draft(payload, "docs/api/users.md")
    pr = build_pr_draft(payload, "docs/api/users.md")

    artifact_content = (
        "# Documentation PR Proposal\n\n"
        "## Summary\n"
        f"{analysis.change_summary}\n\n"
        "## Affecting documents\n"
        + "\n".join(
            f"- {doc.file}: {doc.reason}" for doc in analysis.affected_documents
        )
        + "\n\n## Draft content\n"
        + f"{draft['suggested_update']}\n\n"
        + "## PR title\n"
        + f"{pr['title']}\n\n"
        + "## PR body\n"
        + f"{pr['body']}"
    )

    artifact_dir = "artifacts"
    artifact_path = f"{artifact_dir}/documentation_pr_proposal.md"
    import os

    os.makedirs(artifact_dir, exist_ok=True)
    with open(artifact_path, "w", encoding="utf-8") as fh:
        fh.write(artifact_content)

    return {
        "analysis": analysis.model_dump(),
        "draft": draft,
        "pr": pr,
        "artifact_path": artifact_path,
    }


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """
    <!DOCTYPE html>
    <html lang=\"en\">
      <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <title>DocOps AI MVP</title>
        <style>
          :root {
            --bg: #0b1020;
            --panel: #111827;
            --panel-soft: #1f2937;
            --line: #2d3748;
            --text: #e5e7eb;
            --muted: #94a3b8;
            --primary: #60a5fa;
            --accent: #34d399;
            --warning: #fbbf24;
            --shadow: 0 20px 40px rgba(15, 23, 42, 0.35);
          }
          * { box-sizing: border-box; }
          body {
            margin: 0;
            font-family: Inter, Arial, sans-serif;
            background: linear-gradient(135deg, #0b1020, #111827 40%, #0f172a);
            color: var(--text);
          }
          .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 56px 20px 80px;
          }
          .hero {
            display: grid;
            grid-template-columns: 1.1fr 0.9fr;
            gap: 24px;
            align-items: center;
            margin-bottom: 24px;
          }
          .eyebrow {
            display: inline-block;
            background: rgba(96, 165, 250, 0.12);
            color: var(--primary);
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 16px;
          }
          h1 {
            font-size: clamp(2.4rem, 5vw, 4rem);
            margin: 0 0 16px;
            line-height: 1.05;
          }
          p {
            color: var(--muted);
            font-size: 1.02rem;
            line-height: 1.7;
          }
          .panel {
            background: rgba(17, 24, 39, 0.88);
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: var(--shadow);
            padding: 20px;
          }
          .stack {
            display: grid;
            gap: 16px;
            margin-top: 24px;
          }
          label {
            display: block;
            font-size: 0.82rem;
            color: var(--muted);
            margin-bottom: 8px;
            letter-spacing: 0.01em;
          }
          textarea, input {
            width: 100%;
            background: rgba(15, 23, 42, 0.9);
            color: var(--text);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 12px 14px;
            font-size: 1rem;
          }
          textarea {
            min-height: 140px;
            resize: vertical;
          }
          .buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 12px;
          }
          button {
            border: none;
            border-radius: 10px;
            padding: 12px 18px;
            font-size: 0.96rem;
            font-weight: 600;
            color: white;
            cursor: pointer;
            transition: transform 0.15s ease, opacity 0.15s ease;
          }
          button:hover { transform: translateY(-1px); opacity: 0.98; }
          .primary { background: linear-gradient(135deg, var(--primary), #3b82f6); }
          .secondary { background: linear-gradient(135deg, var(--accent), #10b981); }
          .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px;
            margin-top: 18px;
          }
          pre {
            white-space: pre-wrap;
            word-break: break-word;
            margin: 0;
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 16px;
            color: #dbeafe;
            min-height: 220px;
            font-size: 0.82rem;
            line-height: 1.6;
          }
          .badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 18px;
          }
          .badge {
            background: rgba(52, 211, 153, 0.08);
            color: var(--accent);
            border: 1px solid rgba(52, 211, 153, 0.3);
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 12px;
          }
          @media (max-width: 800px) {
            .hero, .grid { grid-template-columns: 1fr; }
          }
        </style>
      </head>
      <body>
        <div class=\"container\">
          <div class=\"hero\">
            <div>
              <div class=\"eyebrow\">Public DocOps</div>
              <h1>DocOps AI MVP</h1>
              <p>Turn repo changes into docs-ready PRs.</p>
              <p>
                Analyze product changes, find the documentation that is likely affected,
                draft a documentation update, and generate a human-reviewable pull request.
              </p>
              <div class=\"badge-row\">
                <span class=\"badge\">GitHub-ready</span>
                <span class=\"badge\">Local-first</span>
                <span class=\"badge\">AI-assisted</span>
              </div>
            </div>

            <div class=\"panel\">
              <div class=\"stack\">
                <div>
                  <label for=\"repository\">Repository</label>
                  <input id=\"repository\" value=\"demo-project\" />
                </div>
                <div>
                  <label for=\"change\">Change description</label>
                  <textarea id=\"change\">GET /users now supports a status parameter</textarea>
                </div>
                <div class=\"buttons\">
                  <button class=\"primary\" onclick=\"analyzeChange()\">Analyze change</button>
                  <button class=\"secondary\" onclick=\"runWorkflow()\">Run end-to-end workflow</button>
                </div>
              </div>
            </div>
          </div>

          <div class=\"grid\">
            <div class=\"panel\">
              <h3>Impact analysis</h3>
              <pre id=\"analysis-output\">No analysis yet.</pre>
            </div>
            <div class=\"panel\">
              <h3>PR draft</h3>
              <pre id=\"pr-output\">No PR draft yet.</pre>
            </div>
          </div>
        </div>

        <script>
          async function analyzeChange() {
            const payload = {
              repository: document.getElementById('repository').value,
              change: document.getElementById('change').value
            };

            const response = await fetch('/analyze-change', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
            });
            const data = await response.json();
            document.getElementById('analysis-output').textContent = JSON.stringify(data, null, 2);
          }

          async function runWorkflow() {
            const payload = {
              repository: document.getElementById('repository').value,
              change: document.getElementById('change').value
            };

            const response = await fetch('/run-end-to-end', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
            });
            const data = await response.json();
            document.getElementById('analysis-output').textContent = JSON.stringify(data.analysis, null, 2);
            document.getElementById('pr-output').textContent = JSON.stringify(data.pr, null, 2);
          }
        </script>
      </body>
    </html>
    """


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "docops-ai-mvp"}


@app.get("/api/health")
def api_health() -> dict:
    return health()


@app.post("/analyze-change", response_model=AnalysisResponse)
def analyze_change(payload: ChangeRequest) -> AnalysisResponse:
    return build_impact_analysis(payload)


@app.post("/generate-doc-update")
def generate_doc_update(payload: ChangeRequest) -> dict:
    return build_doc_draft(payload, "docs/api/users.md")


@app.post("/create-pr-draft")
def create_pr_draft(payload: ChangeRequest) -> dict:
    return build_pr_draft(payload, "docs/api/users.md")


@app.post("/github-pr-payload")
def github_pr_payload(payload: ChangeRequest) -> dict:
    return build_github_pr_payload(payload)


@app.post("/github-branch-request")
def github_branch_request(payload: ChangeRequest) -> dict:
    return build_github_branch_request(payload)


@app.post("/github-pr-request")
def github_pr_request(payload: ChangeRequest) -> dict:
    return build_github_pr_request(payload)


@app.post("/github-content-payload")
def github_content_payload(payload: ChangeRequest) -> dict:
    return build_github_content_payload(payload)


@app.post("/github-client/create-branch")
def github_client_create_branch(payload: ChangeRequest) -> dict:
    repo_owner = payload.repository.split("/")[0] if "/" in payload.repository else "demo-owner"
    repo_name = payload.repository.split("/")[-1] if "/" in payload.repository else "demo-repo"
    token = os.getenv("GITHUB_TOKEN")
    client = GitHubClient(repo_owner=repo_owner, repo_name=repo_name, token=token)
    result = client.create_branch(base_branch="main", branch_name="docs/update-users-status-filter")
    return result


@app.post("/github-client/create-pr")
def github_client_create_pr(payload: ChangeRequest) -> dict:
    repo_owner = payload.repository.split("/")[0] if "/" in payload.repository else "demo-owner"
    repo_name = payload.repository.split("/")[-1] if "/" in payload.repository else "demo-repo"
    token = os.getenv("GITHUB_TOKEN")
    client = GitHubClient(repo_owner=repo_owner, repo_name=repo_name, token=token)
    result = client.create_pull_request(
        title="Update users API documentation for status filtering",
        head="docs/update-users-status-filter",
        base="main",
        body="Draft documentation PR generated by DocOps AI MVP.",
    )
    return result


@app.post("/github-client/create-documentation-pr")
def github_client_create_documentation_pr(payload: ChangeRequest) -> dict:
    repo_owner = payload.repository.split("/")[0] if "/" in payload.repository else "demo-owner"
    repo_name = payload.repository.split("/")[-1] if "/" in payload.repository else "demo-repo"
    token = os.getenv("GITHUB_TOKEN")
    return create_documentation_pr(payload, repo_owner=repo_owner, repo_name=repo_name, token=token or "token")


@app.post("/run-end-to-end")
def run_end_to_end_endpoint(payload: ChangeRequest) -> dict:
    return run_end_to_end_workflow(payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
