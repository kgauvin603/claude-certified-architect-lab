# Claude Certified Architect Lab

This repo is an SDK-first practice lab for Anthropic's Claude Certified Architect scenarios.

## Accessing the Live Lab

The lab service is deployed and accessible at the following URLs:

| Interface | URL | Purpose |
|-----------|-----|---------|
| **Live Lab UI** | http://cca.keithgauvin.activeadvantage.co:8000/lab | Primary human-facing interface for running scenarios, watching orchestration, viewing trace output, and reading exam explanations. |
| **Swagger UI** | http://cca.keithgauvin.activeadvantage.co:8000/docs | Raw API testing interface for `POST /chat`, `GET /healthz`, `GET /traces`, and all other endpoints. |
| **Health Check** | http://cca.keithgauvin.activeadvantage.co:8000/healthz | Quick readiness check to confirm the lab service is running. |
| **Trace Viewer** | http://cca.keithgauvin.activeadvantage.co:8000/traces | Optional endpoint returning structured trace output for recent agent runs. |

## Runtime model

- Primary runtime: `claude_agent_sdk`
- Stateful support sessions: `ClaudeSDKClient`
- One-shot extraction/evals: `query()`
- Core tools: SDK-native tools exposed through an in-process MCP server
- External FastMCP server remains in the repo for interoperability testing and exam practice

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
pytest -q
uvicorn src.main:app --reload
```

## Notes

The Agent SDK requires the Claude Code CLI to be installed separately.

```bash
npm install -g @anthropic-ai/claude-code
```
