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

## 2026-01-19 - [Mesh Screenshot Caching]
**Learning:** PyVista rendering for screenshots is CPU-intensive (~0.2s for simple meshes). Repeated requests for the same visualization parameters are common.
**Action:** Implemented an in-memory LRU cache keyed by file mtime and visualization parameters. Safely handles unhashable inputs (lists) by converting to tuples. Speedup > 100x.

## 2026-03-10 - [Probabilistic Cache Cleanup]
**Learning:** Frequent file-based cache cleanup involving `os.scandir()` and `stat()` calls on all files (O(N)) adds significant latency (e.g., ~12ms per call for 2000 files) to the hot path of request handling.
**Action:** Implemented probabilistic cleanup (running only 10% of the time). This amortizes the cost of maintenance, reducing average overhead by 90% (to ~1.3ms) while maintaining approximate cache limits.

## 2026-05-15 - [Bytes Search Performance]
**Learning:** In Python, searching for a substring in bytes (`b"sub" in data`) is ~10-12x slower than the string equivalent (`"sub" in data`). For high-throughput parsing (like large log files), using `re.search` on bytes directly is significantly faster than using `in` as a pre-check, and also avoids the overhead of `decode()`.
**Action:** When parsing large binary or ASCII-compatible files, prefer using compiled bytes-regex (`re.compile(rb"...")`) and skip the `in` operator pre-check if the data is `bytes`.

## 2026-01-24 - [Flask-Only Concurrency Strategy]
**Learning:** Hybrid deployments (Flask + Uvicorn) introduced significant complexity and overhead for simple real-time needs.
**Action:** Adopted a Flask-only architecture with `threaded=True`. Pure Flask with threading is sufficient for handling concurrent log streaming and plot polling without the complexity of a separate ASGI server or WebSocket layer.

## 2026-01-24 - [Flask Streaming & Compression]
**Learning:** `Flask-Compress` (gzip) buffers generator outputs until it has a "worthwhile" chunk or the stream ends. This kills real-time responsiveness for log streaming.
**Action:** Use `stream_with_context` to keep the request context active and set `mimetype='text/plain'` (which is often excluded from default compression rules) to force immediate chunk delivery.

## 2026-01-24 - [Docker Volume Permissions]
**Learning:** Binding a host directory that doesn't exist causes Docker to create it as `root`. This causes "Permission denied" errors for the app running as a normal user.
**Action:** Always verify/create directories with correct ownership on the host *before* passing them to `volumes` in `client.containers.run`.

