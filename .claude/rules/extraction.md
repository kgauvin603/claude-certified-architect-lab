Apply when editing extraction logic, schemas, or prompts.

- JSON output must match Pydantic models.
- Nullable fields must use `null`, not empty strings, unless the schema says otherwise.
- Add at least one negative test with missing required fields.
- Use a validation-and-retry loop for recoverable failures.
