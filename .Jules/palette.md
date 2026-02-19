## 2025-02-19 - [Refresh Button Pattern]
**Learning:** The application uses a consistent pattern for 'Refresh' buttons: manually injecting a spinner SVG and 'Refreshing...' text, disabling the button, and restoring original HTML in 'finally'. It does NOT use the 'temporarilyShowSuccess' helper for these (which shows a checkmark), likely because refresh is an idempotent status check rather than a state-changing action.
**Action:** When adding or improving refresh buttons, follow the manual spinner injection pattern rather than using generic success helpers.
