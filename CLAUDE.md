# Project Instructions

You are working in a Claude Certified Architect prep repo.

Primary goals:
- Prefer explicit, auditable designs over clever hidden behavior.
- Use structured outputs for extraction tasks.
- Never silently guess when tools are ambiguous.
- Escalate when policy is unclear, the user requests a human, or progress stalls.
- Keep subagent context minimal and task-specific.

Coding rules:
- Use Python 3.11+
- Prefer Pydantic for schemas.
- Return structured errors with `category` and `retryable`.
- Keep functions small and testable.
- Add tests for tool disambiguation and validation failures.

Workflow rules:
- After editing Python files, run unit tests.
- For extraction prompts, keep prompt and schema aligned.
- For ambiguous user intent, either disambiguate or choose the dedicated search tool.

Agent runtime:
- The primary runtime is the Python Agent SDK (`claude_agent_sdk`), not the plain Messages API.
- Use `ClaudeSDKClient` for stateful support sessions.
- Use `query()` for one-shot extraction and evaluation tasks.
- Prefer SDK in-process MCP via `create_sdk_mcp_server()` for core runtime tools.
- Keep external FastMCP servers only for MCP interoperability testing.
