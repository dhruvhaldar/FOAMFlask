## 2025-05-23 - [Keyboard Accessible Logs]
**Learning:** Scrollable read-only regions (like logs) are inaccessible to keyboard users if they lack `tabindex="0"`, preventing scrolling via arrow keys.
**Action:** Always add `tabindex="0"` and an appropriate role (e.g., `role="log"`) to scrollable output containers to ensure they are keyboard focusable and scrollable.

## 2025-05-23 - [Visible Focus for Hidden Elements]
**Learning:** Interactive elements hidden by `opacity-0` (common for hover-only controls) are invisible to keyboard users when focused, violating accessibility standards.
**Action:** Always pair `opacity-0` with `focus:opacity-100` (for buttons) or `focus-within:opacity-100` (for containers) to ensure controls become visible when they receive keyboard focus.
