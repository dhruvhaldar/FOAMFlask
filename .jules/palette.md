## 2025-05-18 - Feedback on Data Refresh Actions
**Learning:** Users often click "Refresh" buttons and are unsure if the action was registered or if the data simply hasn't changed.
**Action:** Always provide immediate visual feedback (loading spinner, disabled state) on "Refresh" actions, even if the backend response is expected to be fast. A success notification ("List refreshed") also confirms the action completed.

## 2025-05-20 - State-Aware Navigation Icons
**Learning:** Mobile users rely heavily on visual cues for navigation state. A static "hamburger" icon that doesn't change when the menu is open creates cognitive dissonance and hides the "Close" affordance.
**Action:** Implement state-aware transitions for navigation toggles (e.g., morphing hamburger to 'X') and ensure `aria-expanded` attributes are synchronized to support both visual and screen reader users.
