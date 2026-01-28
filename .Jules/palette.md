## 2025-05-24 - Accessible Button Icons
**Learning:** Purely decorative SVG icons inside buttons that already have clear text labels should have `aria-hidden="true"` to prevent screen readers from announcing them as "group" or "image", which adds noise.
**Action:** Always add `aria-hidden="true"` to decorative `<svg>` elements when the parent element has sufficient accessible text content.
