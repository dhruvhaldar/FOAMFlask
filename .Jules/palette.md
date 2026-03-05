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
## 2026-03-01 - Added missing aria-labels to main action buttons
**Learning:** Adding explicit aria-labels and descriptive titles to primarily icon-or-text action buttons (like 'Create Case', 'Update View', etc.) makes the UI significantly more accessible for screen readers without altering visual layout. Found that many key action buttons were missing comprehensive descriptions.
**Action:** Always check form and primary interaction buttons for accessibility context beyond their visual text, especially in dynamic applications.

## 2026-03-03 - Focus Rings for Dynamically Generated Interactive Elements
**Learning:** In heavily dynamic UI frameworks or vanilla JS applications, elements that are dynamically injected into the DOM (like the `.copyable-value` buttons in the Geometry and Mesh info panels) are often overlooked for basic accessibility styling compared to their static counterparts. Specifically, failing to include keyboard focus rings (`focus:outline-none focus:ring-2`) makes them invisible to keyboard-only users navigating the interface.
**Action:** Always cross-reference the styles applied to interactive elements in static HTML with their equivalents generated in TypeScript/JavaScript template strings. Create a shared styling constant or strictly ensure focus-visible styles are manually added to all dynamically created buttons and links.

## $(date +%Y-%m-%d) - [Decorative SVGs Accessibility]
**Learning:** Found that many `<svg>` icons used inside buttons and links lacked the `aria-hidden="true"` attribute. This causes screen readers to potentially read out meaningless or confusing descriptions for these SVG elements, when the parent button's text or `aria-label` is already sufficient.
**Action:** Always add `aria-hidden="true"` to purely decorative `<svg>` elements inside interactive components to streamline the experience for screen reader users.
