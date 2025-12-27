## 2024-05-23 - [Accessible Form Inputs]
**Learning:** Found a pattern of grouped inputs (Min/Max) sharing a single visual label but lacking individual accessible names, confusing screen readers.
**Action:** Always check grouped inputs (like coordinates or ranges) and ensure each has a unique `aria-label` if it lacks a dedicated `<label>`.

## 2024-05-23 - [Lockfile Caution]
**Learning:** Running `pnpm install` in an npm-based project (with `package-lock.json`) generates a `pnpm-lock.yaml`. This should not be committed unless the intent is to switch package managers.
**Action:** Always delete generated lockfiles if not explicitly migrating package managers.

## 2025-02-17 - [Disconnected Labels]
**Learning:** Found a pattern of labels visually positioned near inputs but programmatically disconnected (missing `for` attributes), making forms inaccessible to screen reader users who can't see the visual layout.
**Action:** Systematically check all `<label>` elements during code review to ensure they have a corresponding `for` attribute matching an input's `id`.

## 2025-02-17 - [Tooltip Accessibility]
**Learning:** Tooltips implemented with only `hover` states are inaccessible to keyboard users and screen readers. Information hidden in these tooltips is effectively invisible to a segment of users.
**Action:** Use focusable elements (like `<button>`) for tooltip triggers, ensure `focus` visibility, and link the tooltip text using `aria-describedby` or `role="tooltip"`.
