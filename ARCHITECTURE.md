# Architecture

## High-level architecture

```text
GitHub / local repo
    ↓
Webhook or local trigger
    ↓
FastAPI service
    ├── Change parsing
    ├── Impact analysis
    ├── Documentation generation
    └── Validation
    ↓
MkDocs site
    ↓
Preview / approval / publish
```

## Components

### 1. Source layer

This includes:

- source code
- OpenAPI specs
- documentation markdown
- release notes and issue metadata

### 2. Application layer

FastAPI handles:

- health checks
- analyzing code changes
- mapping docs to code changes
- generating documentation updates
- exposing endpoints used by the UI or automation layer

### 3. AI layer

A local LLM route is used for:

- impact analysis
- summarization
- drafting documentation updates
- structured output generation

### 4. Documentation layer

MkDocs Material renders the approved docs and provides a stable publishing mechanism.

### 5. Review layer

The documentation diff is reviewed by technical writers and developers before publishing.

## Design principles

- keep the first version simple and local
- prefer docs-as-code workflows
- keep AI as an assistant, not a direct publisher
- enforce structure with JSON output and validation checks
- avoid over-engineering before the first milestone is proven
