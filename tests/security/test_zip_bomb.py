import unittest
import io
import gzip
import sys
import os

# Ensure backend is importable
sys.path.append(os.getcwd())

from backend.utils import safe_decompress

class TestZipBomb(unittest.TestCase):
    def test_safe_decompress_limit(self):
        """Test that safe_decompress raises ValueError when limit is exceeded."""

        # Create a compressed stream that expands to more than the limit
        # We'll use a small limit for testing (e.g. 1KB)
        limit = 1024

        # Create data slightly larger than limit (e.g. 2KB of zeros)
        data = b'\x00' * (limit + 100)

        # Compress it
        compressed_buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=compressed_buffer, mode='wb') as f:
            f.write(data)
        compressed_buffer.seek(0)

        # Input stream wrapper
        # We can pass GzipFile directly if it supports read
        source_stream = gzip.GzipFile(fileobj=compressed_buffer, mode='rb')
        dest_stream = io.BytesIO()

        # Check if it raises ValueError
        with self.assertRaises(ValueError) as cm:
            safe_decompress(source_stream, dest_stream, max_size=limit)

        self.assertIn("Decompressed file size exceeds limit", str(cm.exception))

    def test_safe_decompress_within_limit(self):
        """Test that safe_decompress works for files within limit."""
        limit = 1024
        data = b'\x00' * (limit - 100)

        compressed_buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=compressed_buffer, mode='wb') as f:
            f.write(data)
        compressed_buffer.seek(0)

        source_stream = gzip.GzipFile(fileobj=compressed_buffer, mode='rb')
        dest_stream = io.BytesIO()

        safe_decompress(source_stream, dest_stream, max_size=limit)

        self.assertEqual(dest_stream.getvalue(), data)

if __name__ == '__main__':
    unittest.main()
