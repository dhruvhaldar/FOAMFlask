## 2025-02-23 - Realtime Log Parsing Optimization
**Learning:** Python's `string.strip()` and slicing create copies, which can add up in high-frequency parsing loops. Using `index`-based parsing and `find()` allows avoiding intermediate allocations. However, manual parsing in Python loops (character by character) is much slower than C-optimized string methods. The sweet spot is using C-methods like `find()` to determine indices and then slicing only the final result.
**Action:** When optimizing string parsing in Python, prefer `find()`/`index()` to locate delimiters and slice once, rather than iteratively stripping/splitting which creates garbage. Also, avoid `while` loops over string characters in Python.

## 2025-02-23 - OS System Call Reduction
**Learning:** `os.stat()` is a relatively expensive system call, especially when called frequently in a loop (e.g., polling directory contents). `os.scandir` on POSIX systems caches file type information but NOT mtime (unless the OS returns it in the dirent, which Python's `os.DirEntry.stat()` handles but might still trigger a syscall if not cached). Calling `stat()` multiple times on the same file in a single logic flow (e.g. once for type check, once for mtime extraction) is wasteful.
**Action:** Capture `stat` results (like mtime) once and pass them down the call stack. Also, verify if a check (like file type) can be inferred from other sources (like a filename cache) to avoid the `stat` call entirely.

## 2025-02-23 - Regex vs Set Intersection for Character Validation
**Learning:** While `set(string).isdisjoint(DANGEROUS_CHARS)` is fast in pure Python, it incurs a significant overhead due to the allocation of a `set` on every function call. A pre-compiled regular expression `re.compile(r'[;&|`$()<>"\'*?\[\]~!\n\r{}\\\\#]')` searching over the string is over 2x faster, eliminating the allocation bottleneck.
**Action:** Prefer pre-compiled regular expressions for simple character exclusion checks on high-frequency validation functions instead of dynamically constructing sets.
