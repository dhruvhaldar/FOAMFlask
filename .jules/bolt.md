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

## 2026-06-22 - [Flask-Compress & Streaming Performance]
**Learning:** `Flask-Compress` buffers responses with `text/html` mimetype, destroying the real-time nature of streaming endpoints (like log tailing). This results in the user seeing nothing until the buffer fills or the stream ends.
**Action:** For streaming endpoints, use `stream_with_context`, set mimetype to `text/plain` (or another uncompressed type), and ensure the client handles raw text streams (newline-delimited) instead of expecting HTML chunks. This bypasses compression buffering and ensures immediate delivery of each chunk.

## 2026-10-27 - [Frontend DOM Limits]
**Learning:** Unbounded DOM growth from streaming logs causes severe browser lag. Limiting cached HTML string size is insufficient if the actual DOM nodes are not pruned.
**Action:** Implement a hard limit on DOM nodes (e.g. 2500) for log containers. Use a hysteresis approach (prune to 2000 when hitting 2500) to avoid expensive DOM removal operations on every single update. Ensure this check runs in both buffered and direct streaming paths.

## 2026-10-27 - [Redundant Log Monitoring]
**Learning:** A background thread was polling for the simulation log file (`log.foamRun`) to copy it to a secondary file (`foamrun_logs.txt`). This secondary file was never read by the frontend or backend, resulting in wasted I/O and unnecessary thread creation.
**Action:** Removed the `monitor_foamrun_log` function and the thread creation logic. This eliminates unnecessary context switching and disk I/O without affecting functionality.

## 2027-04-12 - [Regex Compilation Overhead]
**Learning:** Compiling regex patterns (`re.compile`) inside high-frequency loops (like variable resolution in large data files) adds significant CPU overhead, even with Python's internal cache, due to string construction and hashing.
**Action:** Extract dynamic regex generation to a helper function decorated with `functools.lru_cache`. This caches the compiled `re.Pattern` object based on the variable name, avoiding repeated compilation and string manipulation. Benchmarks showed an 8x speedup for pattern generation.

## 2027-04-14 - [Regex Anchoring and Manual Parsing]
**Learning:** Searching for a prefix (e.g. `Time =`) using an unanchored regex (`re.search(r"Time =")`) is inefficient because the regex engine scans the entire string (or line) for a match. For high-throughput log parsing where most lines do NOT match the prefix, this O(N) scan per line is costly.
**Action:** Replace unanchored regex search with `startswith()` checks or anchored regex (`^Time`). Furthermore, for simple formats, manual parsing (e.g., `split('=')`) can be faster than regex extraction. This yielded a ~30% speedup in parsing log lines.

## 2027-05-20 - [Persistent Mesh Visualization Caching]
**Learning:** `MeshVisualizer` was clearing its entire LRU cache (`_html_cache`) every time a new mesh was loaded. This meant switching between two meshes (A -> B -> A) triggered a full reload and re-processing (disk I/O + decimation + HTML export) for A, destroying the benefits of caching for multi-file workflows.
**Action:** Removed the `_html_cache.clear()` call in `load_mesh`. Updated `get_interactive_viewer_html` to check the cache (using path and mtime) *before* invoking the expensive `load_mesh` method. This enables instant switching between previously viewed meshes without re-processing.

## 2026-06-25 - [Compressed Geometry File Handling]
**Learning:** The `BaseVisualizer` class strictly validated file extensions against a hardcoded set (e.g., `.stl`, `.obj`), causing unnecessary "Invalid file extension" errors for valid compressed geometry files like `.stl.gz` and `.obj.gz`, even though the underlying loading logic supported gzip decompression.
**Action:** Updated `BaseVisualizer` to explicitly allow `.obj.gz` and `.stl.gz` extensions and modified the validation logic to correctly handle multi-part extensions. This enables seamless visualization of compressed geometry files without user intervention.
## 2026-02-12 - [Robust Value Extraction with Suffixes]
**Learning:** Manual string splitting and `float()` conversion (e.g., `line.split('=')[1]`) are fragile when dealing with external log outputs that may include units or suffixes (e.g., `Time = 24s`). This causes silent or loud failures in parsing loops.
**Action:** Prefer using pre-compiled regex with specific capture groups for numeric extraction. This approach robustly handles extra characters like 's' or 'ms' and trailing whitespace, while remaining high-performance.

