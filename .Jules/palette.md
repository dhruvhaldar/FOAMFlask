## 2026-02-06 - Native Form Validation UX
**Learning:** Browser native validation (`invalid:` pseudo-class) creates poor UX for `required` fields by triggering error styles immediately on page load (because the field is initially empty).
**Action:** Use the `input:not(:placeholder-shown):invalid` pattern (Tailwind: `[&:not(:placeholder-shown):invalid]:...`) to defer error styling until the user has interacted with the field.

## 2026-02-07 - Semantic Accordions
**Learning:** Replacing custom Javascript-driven "accordions" (div toggling) with semantic `<details>` and `<summary>` elements provides immediate accessibility benefits (keyboard nav, screen reader state) and reduces code complexity.
**Action:** Prefer `<details>`/`<summary>` for collapsible sections over custom button+div implementations.
