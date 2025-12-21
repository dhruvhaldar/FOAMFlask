## 2025-12-12 - [Frontend Storage Bottleneck]
**Learning:** Writing to `localStorage` synchronously in a high-frequency loop (like log streaming) blocks the main thread and causes UI jank. Even with DOM debouncing, the serialization of large innerHTML strings is expensive.
**Action:** Decouple data persistence from UI rendering. Use a separate, longer debounce timer (e.g., 2000ms) for storage operations, while keeping UI updates snappy (e.g., 16ms or rAF).

## 2024-05-24 - [Backend File Polling]
**Learning:** `pathlib.Path.stat()` can be a significant bottleneck when called frequently in a loop (e.g., 250+ calls/sec) on many files, especially in Docker/bound mount environments.
**Action:** For time-series data where historical files are immutable (like OpenFOAM time directories), skip `stat()` checks for all but the latest time step by trusting the application cache. This reduces IOPS from O(N) to O(1) per poll.
