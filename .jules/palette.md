## 2026-02-14 - Accessible Tabs (Roving Tabindex)
**Learning:** Custom tab implementations using `role="tablist"` often default to standard button behavior (Tab key navigation), which is tedious for users with many tabs. The standard accessible pattern is "Roving Tabindex" where Arrow keys navigate *within* the tablist, and the Tab key exits the list.
**Action:** Implement a keyboard event listener for Arrow keys to manage focus within the group, and manage `tabindex` (0 for active, -1 for others) to allow seamless navigation.
