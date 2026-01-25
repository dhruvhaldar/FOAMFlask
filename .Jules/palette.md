## 2025-05-15 - [Error Feedback Pattern]
**Learning:** Frontend functions using `fetch` or `fetchWithCache` were systematically swallowing specific error messages returned by the backend in the JSON body (e.g., `{"output": "Invalid path"}`), defaulting to generic "Failed" messages. This leaves users confused about validation errors.
**Action:** When handling fetch errors (`!response.ok`), always attempt to parse the response body as JSON and extract `message`, `error`, or `output` fields to display in notifications, falling back to status text only if parsing fails.
