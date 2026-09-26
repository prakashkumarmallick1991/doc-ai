# AI Architecture

## Goal

Use AI to make documentation work more useful, not less controlled.

## AI responsibilities

- detect likely impacted documentation
- explain why a doc is affected
- suggest the missing information
- generate a documentation draft based on an API change
- produce structured outputs for review and validation

## Local-first AI design

```text
FastAPI app
   ↓
AI gateway
   ├── model router
   ├── prompt management
   ├── structured output parsing
   └── guardrails
   ↓
Ollama / local model
```

## Suggested model strategy

For MVP, prefer a smaller but reliable model such as:

- Qwen 2.5 or similar lightweight local model
- relevant open-weight model that runs on local hardware

## Guardrails

- require structured JSON output
- validate generated content before PR creation
- require human review before merge
- block direct write access to production docs

## Why this matters

A production-ready documentation platform needs outputs that are explainable, reviewable, and traceable to source materials rather than free-form text without context.
