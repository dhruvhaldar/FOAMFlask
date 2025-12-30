## 2025-05-23 - [Keyboard Accessible Logs]
**Learning:** Scrollable read-only regions (like logs) are inaccessible to keyboard users if they lack `tabindex="0"`, preventing scrolling via arrow keys.
**Action:** Always add `tabindex="0"` and an appropriate role (e.g., `role="log"`) to scrollable output containers to ensure they are keyboard focusable and scrollable.
