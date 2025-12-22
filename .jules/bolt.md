# Bolt's Journal

## 2024-05-22 - [Frontend Polling Optimization]
**Learning:** The frontend was polling `/api/plot_data` and `/api/residuals` every 1000ms unconditionally. This caused significant network overhead and potential UI jank, especially when no simulation was running or when the tab was in the background.
**Action:** Implemented a check for `document.hidden` to pause polling when the tab is inactive. Also, added logic to only poll when a simulation is actually running (or expected to change). This pattern of "intelligent polling" should be applied to all future real-time features.

## 2024-05-23 - [Log Parsing Optimization]
**Learning:** The backend was re-reading the entire log file on every poll request to parse residuals. As the log file grew (which happens quickly in OpenFOAM), this became O(N) where N is the file size, for every request.
**Action:** Implemented a caching mechanism that stores the file offset. We now seek to the last known position and only read new lines. This makes the operation O(K) where K is the new data size. Always look for "append-only" data patterns and optimize reading strategies accordingly.

## 2024-05-24 - [OpenFOAM Field Parsing Optimization]
**Learning:** `re.findall` with complex regex patterns on large text blocks (OpenFOAM field files) is extremely slow.
**Action:** Replaced regex-based parsing with `numpy.fromstring` (after light text preprocessing to handle OpenFOAM's vector format). This resulted in a 10-20x speedup for loading large field data. Lesson: For heavy numerical parsing, avoid Regex and Python loops; use C-optimized libraries like NumPy whenever possible.

## 2024-05-25 - [Frontend DOM Updates]
**Learning:** The `appendOutput` function in the frontend was causing layout thrashing by constantly manipulating the DOM and forcing reflows for every log chunk, even if the user wasn't scrolling.
**Action:** Implemented a "smart scroll" feature. We now check if the user is at the bottom *before* appending. If they are, we scroll to the new bottom. If they have scrolled up, we maintain their position. This improves the UX and reduces the browser's rendering load.

## 2024-05-25 - [Filesystem Metadata Caching]
**Learning:** `backend/plots/realtime_plots.py` was calling `os.stat` and `os.path.exists` repeatedly for every time step directory during polling, which is expensive on some filesystems (especially Docker bind mounts on Windows).
**Action:** Introduced `_FILE_CACHE` to treat historical time directories as immutable. Once a time directory is processed, we cache its existence and don't check it again. We only check the latest time step. This significantly reduced I/O overhead.

## 2024-05-25 - [Frontend Render Loop]
**Learning:** `appendOutput` was being called too frequently, causing the UI to freeze during rapid log output.
**Action:** Replaced simple invocation with a throttled approach using `requestAnimationFrame` or a 32ms timer (approx 30fps). This ensures the UI remains responsive even when the backend is streaming data at high velocity.
