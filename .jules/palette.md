## 2025-05-23 - [Keyboard Accessible Logs]
**Learning:** Scrollable read-only regions (like logs) are inaccessible to keyboard users if they lack `tabindex="0"`, preventing scrolling via arrow keys.
**Action:** Always add `tabindex="0"` and an appropriate role (e.g., `role="log"`) to scrollable output containers to ensure they are keyboard focusable and scrollable.

## 2025-10-27 - [Hidden Interactive Elements]
**Learning:** Interactive elements that are visually hidden (e.g., `opacity: 0`) until hover are inaccessible to keyboard users unless they are also revealed on focus.
**Action:** When using `opacity-0 group-hover:opacity-100`, always add `focus:opacity-100` (for the element itself) or `focus-within:opacity-100` (for container elements) to ensure keyboard users can see what they are interacting with.
