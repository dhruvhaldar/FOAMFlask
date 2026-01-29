## 2025-05-15 - [Error Feedback Pattern]
**Learning:** Frontend functions using `fetch` or `fetchWithCache` were systematically swallowing specific error messages returned by the backend in the JSON body (e.g., `{"output": "Invalid path"}`), defaulting to generic "Failed" messages. This leaves users confused about validation errors.
**Action:** When handling fetch errors (`!response.ok`), always attempt to parse the response body as JSON and extract `message`, `error`, or `output` fields to display in notifications, falling back to status text only if parsing fails.

## 2026-01-29 - [Form Dependency Visuals]
**Learning:** Users can feel confused when an input field is visually available but logically dependent on a disabled/unchecked parent setting. Relying solely on helper text ("Requires X enabled") is insufficient.
**Action:** Always programmatically toggle the `disabled` state and apply visual cues (e.g., `opacity-50`, `cursor-not-allowed`, `aria-disabled`) to dependent inputs when their parent controller is disabled/unchecked.
