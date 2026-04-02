# Claude Certified Architect Lab

This repo is an SDK-first practice lab for Anthropic's Claude Certified Architect scenarios.

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
