## 2025-12-14 - [Directory Iteration Optimization]
**Learning:** For directories with many entries, `os.scandir()` is significantly faster than `pathlib.Path.iterdir()` because it avoids the overhead of creating a `Path` object for every entry and often provides file type information (`is_dir`, `is_file`) directly from the directory entry without extra `stat()` calls.
**Action:** Prefer `os.scandir()` over `pathlib` for performance-critical directory traversal loops, especially when filtering by file type.

## 2025-12-14 - [ETag Optimization for Polling]
**Learning:** Polling endpoints (like realtime plots) often check a "trigger" file (e.g., log file) to see if update is needed. If the trigger updates frequently (e.g., every log line) but the expensive payload (e.g., field data) updates rarely, the server re-processes data unnecessarily.
**Action:** Implement a secondary check using ETag based on the actual data source mtime (e.g., latest time directory) to return 304 Not Modified even if the primary trigger (log) has changed. This saves significant CPU/IO during "compute-only" phases of simulation.

## 2025-01-27 - [Append-Only Cache Optimization]
**Learning:** For time-series data caches that grow monotonically (like simulation logs), re-copying the entire data structure on every update is O(N²).
**Action:** Detect the "append-only" case (where the new state is a superset of the old state) and use a shallow copy of the container + in-place append for the internal lists. This reduces complexity to O(N) and significantly speeds up polling for long-running processes.

## 2025-02-05 - [Docker Execution Consolidation]
**Learning:** Running `client.containers.run` incurs significant overhead (often 500ms-1s) for container startup and shutdown. When multiple commands need to be run sequentially (e.g., sourcing environment variables then running a command), executing them in separate containers multiplies this latency.
**Action:** Combine sequential shell commands into a single execution using `bash -c 'cmd1 && cmd2'` whenever possible to pay the startup cost only once. This is especially critical for frequently called endpoints or initialization routines.
