## 2025-12-12 - [Frontend Storage Bottleneck]
**Learning:** Writing to `localStorage` synchronously in a high-frequency loop (like log streaming) blocks the main thread and causes UI jank. Even with DOM debouncing, the serialization of large innerHTML strings is expensive.
**Action:** Decouple data persistence from UI rendering. Use a separate, longer debounce timer (e.g., 2000ms) for storage operations, while keeping UI updates snappy (e.g., 16ms or rAF).
