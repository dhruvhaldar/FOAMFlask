## 2024-05-23 - [Accessible Form Inputs]
**Learning:** Found a pattern of grouped inputs (Min/Max) sharing a single visual label but lacking individual accessible names, confusing screen readers.
**Action:** Always check grouped inputs (like coordinates or ranges) and ensure each has a unique `aria-label` if it lacks a dedicated `<label>`.

## 2024-05-23 - [Lockfile Caution]
**Learning:** Running `pnpm install` in an npm-based project (with `package-lock.json`) generates a `pnpm-lock.yaml`. This should not be committed unless the intent is to switch package managers.
**Action:** Always delete generated lockfiles if not explicitly migrating package managers.