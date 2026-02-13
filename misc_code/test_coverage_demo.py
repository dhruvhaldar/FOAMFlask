#!/usr/bin/env python3
"""
Simple test to demonstrate coverage.py functionality.
"""

import os
import sys


def simple_function(x, y):
    """A simple function for testing coverage."""
    if x > 0:
        result = x + y
    else:
        result = x - y
    return result


def another_function(a, b):
    """Another function for testing coverage."""
    if a > b:
        return "greater"
    elif a < b:
        return "less"
    else:
        return "equal"


def test_simple_function():
    """Test the simple function."""
    assert simple_function(5, 3) == 8
    assert simple_function(-5, 3) == -8


def test_another_function():
    """Test another function."""
    assert another_function(10, 5) == "greater"
    assert another_function(5, 10) == "less"
    assert another_function(5, 5) == "equal"


if __name__ == "__main__":
    # Run tests
    test_simple_function()
    test_another_function()
    print("[v] All tests passed!")
