## 2025-12-14 - [Directory Iteration Optimization]
**Learning:** For directories with many entries, `os.scandir()` is significantly faster than `pathlib.Path.iterdir()` because it avoids the overhead of creating a `Path` object for every entry and often provides file type information (`is_dir`, `is_file`) directly from the directory entry without extra `stat()` calls.
**Action:** Prefer `os.scandir()` over `pathlib` for performance-critical directory traversal loops, especially when filtering by file type.
