Apply when editing files under `src/agent/` or `src/mcp_server/`.

- Do not return raw strings for tool failures.
- Always use the structured error envelope.
- Keep retry behavior in the coordinator, not buried inside tools unless transport-specific.
- Separate exact lookup tools from fuzzy search tools.
