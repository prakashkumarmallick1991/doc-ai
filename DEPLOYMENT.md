# Deployment guide

This project is designed to be a public-facing MVP that can run on free infrastructure.

## Recommended free deployment setup

### Option 1: Render (recommended)

1. Push the repo to GitHub.
2. Create a new Render Web Service.
3. Connect the repo.
4. Use the included `render.yaml` config.
5. Set environment variables in the Render dashboard:
   - `GITHUB_TOKEN` (optional, for real GitHub branch/PR creation)
   - `APP_ENV=production`
6. Deploy.

### Option 2: Docker / any container host

```bash
docker build -t docops-ai-mvp .
docker run -p 8000:8000 --env-file .env docops-ai-mvp
```

### Option 3: Local public tunnel for demos

Use a tunnel tool for a temporary public demo, but Render is the better long-term free deployment target.

## Free-tier architecture

- Frontend: served by the FastAPI app itself in the MVP
- Backend: FastAPI API layer
- AI: local Ollama or free hosted provider
- GitHub: REST API with personal access token
- Storage: none required for MVP; keep everything in repo and memory

## Features that work well for public use

- repo analysis via text input
- suggested impacted docs
- PR draft preview
- optional GitHub branch and PR creation when a token is present
- fast deployment without a database

## Limitations

This is still an MVP and should not be marketed as an enterprise platform. It is best positioned as a public, open-source DocOps assistant for documentation impact analysis and PR generation.

## Suggested future upgrades

- GitHub OAuth login
- public repo URL ingestion
- OpenRouter model provider
- rate limiting
- analytics and usage tracking
- GitLab or Jira connectors
