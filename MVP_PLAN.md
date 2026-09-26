# MVP Plan

## Objective

Build the first end-to-end documentation automation workflow for a local project. The system should detect a code or API change, identify likely impacted docs, generate a draft update, and present it for review.

## MVP scope

### In scope

- FastAPI backend
- local LLM integration via Ollama
- Git diff and API change input handling
- documentation impact analysis
- draft generation for selected docs
- MkDocs-based docs publishing
- local preview and validation

### Out of scope for v1

- Jira/Confluence connectors
- enterprise RBAC
- Kubernetes deployment
- multi-user dashboards
- cloud vector database

## Workflow

1. A developer changes an API or feature.
2. The backend receives change metadata or a diff.
3. The impact analyzer inspects relevant code and OpenAPI data.
4. The system identifies likely docs to update.
5. The AI agent generates structured doc changes.
6. A diff or PR proposal is created for review.
7. MkDocs validates the rendered docs and catches issues.

## API endpoints

- GET /health
- POST /analyze-change
- POST /generate-doc-update

## Data flow

```text
API or code change
   ↓
FastAPI service
   ↓
Impact analysis
   ↓
Relevant sources
   ↓
AI structured draft
   ↓
Review diff/PR
   ↓
MkDocs validation
```

## Deliverables

- backend service with FastAPI
- local LLM integration using Ollama
- demo project with API and docs
- MkDocs site
- basic CLI or API checks for validation

## Definition of done

The MVP is successful when you can:

- change the demo API definition
- analyze the affected documentation set
- generate a patch proposal
- see the generated documentation in the rendered MkDocs site
- verify the flow works without cloud APIs
