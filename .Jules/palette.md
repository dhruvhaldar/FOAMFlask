## 2025-02-19 - [Refresh Button Pattern]
**Learning:** The application uses a consistent pattern for 'Refresh' buttons: manually injecting a spinner SVG and 'Refreshing...' text, disabling the button, and restoring original HTML in 'finally'. It does NOT use the 'temporarilyShowSuccess' helper for these (which shows a checkmark), likely because refresh is an idempotent status check rather than a state-changing action.
**Action:** When adding or improving refresh buttons, follow the manual spinner injection pattern rather than using generic success helpers.

## 2025-05-21 - [Input Validation Feedback]
**Learning:** Inputs in this app (specifically vector inputs like '20 20 20') often lack validation, leading to silent backend failures. Retasking the existing `flashInputFeedback` (originally for 'success' green flashes) to support 'error' red flashes provides a cheap, consistent, and highly visible way to communicate format errors without implementing complex form validation libraries.
**Action:** Use `flashInputFeedback(el, msg, true)` for lightweight client-side validation errors instead of generic toast notifications when the error is specific to an input field.

## 2025-06-12 - [Dynamic Form Feedback Accessibility]
**Learning:** This application extensively uses inline helper text (via `aria-describedby`) to provide dynamic validation or auto-formatting feedback (e.g., formatting vectors or case names on blur). Because this feedback occurs *after* the user's focus has left the field, screen readers will not naturally announce it. Adding `aria-live="polite" aria-atomic="true"` to these helper `<p>` tags ensures the feedback is announced without interrupting the user.
**Action:** Always add `aria-live="polite" aria-atomic="true"` to form helper text elements if their text content is manipulated dynamically by JavaScript.

## 2025-06-12 - [Plotly Keyboard Accessibility]
**Learning:** Plotly modebars (toolbars) are only visible on mouse hover by default (`.plot-container:hover .modebar`). This completely excludes keyboard-only and screen reader users from accessing critical interactive features like zoom, pan, and download.
**Action:** Always append `:focus-within` to the hover CSS rules for Plotly modebars (e.g., `.plot-container:focus-within .modebar`) so that tabbing into the plot container forces the modebar to appear and become operable.
