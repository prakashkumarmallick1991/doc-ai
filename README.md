# DocOps AI MVP

DocOps AI is a local-first documentation automation platform that connects product changes to documentation impact, draft updates, and PR-based review. The goal is to prove one end-to-end workflow:

- a code or API change happens
- the system identifies affected docs
- an AI agent drafts a documentation update
- a pull request is created for human review
- MkDocs validates and publishes the documentation

## Why this project

Most documentation tools fail because they treat writing as a final step instead of a continuous engineering workflow. This project focuses on the real problem: automating the documentation lifecycle from change detection to publishing, while keeping humans in the loop.

## MVP objective

Build a working local MVP that can:

1. read an API change or code diff
2. understand which documentation is likely impacted
3. generate a structured documentation update
4. show the diff to a writer
5. create a documentation PR or patch proposal
6. validate the docs with MkDocs and CI checks

## Production vision

The production system adds:

- GitHub/Jira/Confluence connectors
- AI routing across local and cloud models
- RAG over approved docs
- approval workflows and RBAC
- staging and production deployment
- enterprise-level observability and security

## Stack

- Python 3.12+
- FastAPI
- Ollama + local LLMs
- MkDocs Material
- GitHub for source control and PRs
- Docker Compose for local development

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload
```

Then open:

- http://localhost:8000/
- http://localhost:8000/docs
- http://localhost:8000/health

## How to use it

1. Start the app with the command above.
2. Open the root page at http://localhost:8000/.
3. Enter a change description such as:
   - "GET /users now supports a status parameter"
   - "Add filtering to customer records API"
4. Click "Analyze change" to see impacted documentation and confidence.
5. Click "Run end-to-end workflow" to generate the analysis and the documentation PR draft in the browser.
6. Review the results and adjust the change text if needed before creating a real documentation PR.

The root page provides a lightweight UI for the full local workflow without needing to call the API manually.

## Example workflow

```bash
curl -X POST http://localhost:8000/analyze-change \
  -H "Content-Type: application/json" \
  -d '{"repository":"demo-project","change":"GET /users now supports a status parameter"}'
```

You should receive a JSON payload with:

- change_summary
- affected_documents
- sources
- confidence

The app also includes endpoints for:

- /generate-doc-update
- /create-pr-draft
- /github-pr-payload
- /run-end-to-end

## Repository structure

```text
.
├── README.md
├── PRODUCT_VISION.md
├── MVP_PLAN.md
├── ARCHITECTURE.md
├── AI_ARCHITECTURE.md
├── ROADMAP.md
├── backend/
│   └── app/
│       └── main.py
├── demo-project/
│   ├── openapi.yaml
│   └── src/
│       └── users.py
├── docs/
│   ├── index.md
│   ├── api/
│   └── guides/
├── mkdocs.yml
├── requirements.txt
├── docker-compose.yml
├── .gitignore
└── .github/
```

## First milestone

The first success condition is simple:

> Change an API in the demo project and the system automatically identifies the affected documentation and creates a documentation update proposal.

## Local validation

Before shipping a change, run:

```bash
pytest -q
```

This project includes tests for impact analysis, GitHub payload generation, and end-to-end workflow output.

## Roadmap

- Phase 1: local docs-as-code foundation
- Phase 2: quality checks and MkDocs validation
- Phase 3: GitHub PR generation
- Phase 4: AI-driven impact analysis
- Phase 5: RAG documentation assistant
- Phase 6: enterprise productionization

## License

This project is intended for learning and prototype work.
