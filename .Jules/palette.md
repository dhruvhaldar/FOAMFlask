# Palette's Journal

## 2026-01-15 - Missing Loading States on Async Actions
**Learning:** Users lack feedback during blocking async operations like generating mesh configuration, leading to uncertainty if the action was registered.
**Action:** Always wrap async fetch calls in a try/finally block that toggles a loading state (spinner/disabled) on the triggering button.
