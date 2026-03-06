## 2025-02-23 - Avoiding Redundant Path.exists() Checks
**Learning:** Python backend endpoints frequently incur a double system call overhead when using "Look Before You Leap" (LBYL) code patterns like `if not path.exists(): return error` immediately followed by `os.stat(path)` or `os.scandir(path)`. This is especially costly for high-frequency polling endpoints.
**Action:** When a file or directory operation is intended immediately after checking its existence, replace the explicit `Path.exists()` check with an "Easier to Ask for Forgiveness than Permission" (EAFP) approach. Wrap the primary operation (`os.stat`, `os.scandir`, etc.) in a `try...except FileNotFoundError` (or `OSError`) block and handle the missing file case within the exception handler. Note that corresponding tests mocking `Path.exists` will need to be updated to mock `os.stat` or similar.

## 2025-02-23 - Git Hygiene for Local Databases
**Learning:** Local database files, such as SQLite `.db` files generated during testing or local development (e.g., `instance/simulation_runs.db`), should never be committed to version control. Doing so causes repository bloat, overrides the local state of other developers, and risks leaking sensitive testing data.
**Action:** Always run `git status` before committing to ensure unintended files are not staged. If auto-generated binaries or databases appear, unstage them (`git reset HEAD <file>`), remove them if necessary, and ensure they are covered by `.gitignore`.

## 2025-03-05 - Pre-compiling regexes for validation functions
**Learning:** Calling `re.match` or `re.search` with string literals directly inside functions causes the Python regex engine to perform internal cache lookups. For frequently called functions, especially validation functions used in multiple endpoints, this overhead accumulates.
**Action:** Extract inline regexes to module-level global variables using `re.compile()`, and call `.match()` or `.search()` on the compiled object. This skips the cache lookup step entirely and offers a ~2x performance speedup.
## 2026-03-01 - [Batch NumPy Percentile Calculations]
**Learning:** Calling `np.percentile` multiple times on a large dataset forces NumPy to independently partition or sort the array for each call, leading to O(k*N) complexity. Providing a list of percentiles allows NumPy to optimize the operation.
**Action:** Group multiple percentile queries into a single `np.percentile(data, [p1, p2, p3...])` call and unpack the result.
