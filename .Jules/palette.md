# Palette's Journal

## 2026-01-15 - Missing Loading States on Async Actions
**Learning:** Users lack feedback during blocking async operations like generating mesh configuration, leading to uncertainty if the action was registered.
**Action:** Always wrap async fetch calls in a try/finally block that toggles a loading state (spinner/disabled) on the triggering button.

## 2026-01-20 - Modal Focus Trapping
**Learning:** Custom modals implemented as appended DOM elements often miss keyboard focus management, allowing users to Tab out of the modal into the background page, which violates accessibility standards and confuses screen reader users.
**Action:** Always implement a focus trap loop (handling Tab and Shift+Tab) within custom modals and restore focus to the previously active element upon closure.
