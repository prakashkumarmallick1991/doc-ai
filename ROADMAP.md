# Roadmap

## Phase 1: Local MVP foundation

- set up Git repo and docs-as-code workflow
- create FastAPI app and health endpoint
- define demo API and docs structure
- validate local build with MkDocs

## Phase 2: AI impact analysis

- accept change metadata or diff payload
- classify affected documents
- output structured JSON for review
- connect to local LLM via Ollama

## Phase 3: Documentation generation

- generate patch proposals for selected docs
- compare draft vs existing content
- store review-ready diff output

## Phase 4: GitHub integration

- create PR-ready branches
- generate PR body and summary
- add doc validation checks

## Phase 5: RAG assistant

- index approved docs
- vectorize and query using local or cloud embeddings
- expose documentation Q&A endpoint

## Phase 6: Production upgrade

- Jira, GitHub, and Confluence connectors
- CI/CD deployment with Azure Static Web Apps
- security, RBAC, audit logs, and enterprise workflows


