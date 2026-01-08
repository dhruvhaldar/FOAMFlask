import os
import time
from pathlib import Path

path = Path("test_file")
path.touch()
path_str = str(path)

iterations = 100000

start = time.time()
for _ in range(iterations):
    path.stat()
print(f"Path.stat(): {time.time() - start:.4f}s")

start = time.time()
for _ in range(iterations):
    os.stat(path_str)
print(f"os.stat(): {time.time() - start:.4f}s")

path.unlink()
