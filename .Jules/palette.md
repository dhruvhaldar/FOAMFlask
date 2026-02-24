## 2025-02-19 - [Refresh Button Pattern]
**Learning:** The application uses a consistent pattern for 'Refresh' buttons: manually injecting a spinner SVG and 'Refreshing...' text, disabling the button, and restoring original HTML in 'finally'. It does NOT use the 'temporarilyShowSuccess' helper for these (which shows a checkmark), likely because refresh is an idempotent status check rather than a state-changing action.
**Action:** When adding or improving refresh buttons, follow the manual spinner injection pattern rather than using generic success helpers.

## 2025-05-21 - [Input Validation Feedback]
**Learning:** Inputs in this app (specifically vector inputs like '20 20 20') often lack validation, leading to silent backend failures. Retasking the existing `flashInputFeedback` (originally for 'success' green flashes) to support 'error' red flashes provides a cheap, consistent, and highly visible way to communicate format errors without implementing complex form validation libraries.
**Action:** Use `flashInputFeedback(el, msg, true)` for lightweight client-side validation errors instead of generic toast notifications when the error is specific to an input field.
