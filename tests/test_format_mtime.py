
import pytest
import time
import email.utils
from app import format_mtime

def test_format_mtime_correctness():
    """Verify format_mtime produces correct HTTP date strings."""
    now = time.time()
    # email.utils.formatdate truncates to integer seconds internally if not passed
    # But wait, does it?
    # email.utils.formatdate(timeval) uses time.gmtime(timeval)
    # time.gmtime accepts float.

    expected = email.utils.formatdate(now, usegmt=True)
    # Our optimized version casts to int first.
    # So format_mtime(123.9) -> formatdate(123).
    # original formatdate(123.9) -> gmtime(123.9). gmtime ignores subseconds usually?
    # Python docs: "gmtime() ... fractions of a second are ignored"

    assert format_mtime(now) == expected

def test_format_mtime_optimization():
    """
    Verify that format_mtime uses the cached internal function
    and handles sub-second variations efficiently.
    """
    from app import _format_mtime_cached

    # Clear cache to start fresh
    _format_mtime_cached.cache_clear()

    base_time = 1600000000.0

    # Call 1: Base time
    res1 = format_mtime(base_time)

    # Call 2: Base time + 0.1s (same integer second)
    res2 = format_mtime(base_time + 0.1)

    # Call 3: Base time + 0.9s (same integer second)
    res3 = format_mtime(base_time + 0.9)

    assert res1 == res2 == res3

    # Check cache stats
    info = _format_mtime_cached.cache_info()

    # Should have 1 miss (first call) and 2 hits (subsequent calls)
    # Be robust: ensure hits increased by at least 2
    assert info.misses >= 1
    assert info.hits >= 2

    # Call 4: New second
    format_mtime(base_time + 1.0)
    info_new = _format_mtime_cached.cache_info()
    assert info_new.misses == info.misses + 1
