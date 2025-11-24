#!/usr/bin/env python3
"""
Simple script to check docstring coverage for Python modules.
"""

import ast
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def get_docstring_coverage(module_path: str) -> Tuple[int, int, float]:
    """Calculate docstring coverage for a Python module.
    
    Args:
        module_path: Path to the Python file
        
    Returns:
        Tuple of (documented_items, total_items, coverage_percentage)
    """
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        documented = 0
        total = 0
        
        for node in ast.walk(tree):
            # Check functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total += 1
                if (ast.get_docstring(node) is not None and 
                    ast.get_docstring(node).strip()):
                    documented += 1
            
            # Check classes
            elif isinstance(node, ast.ClassDef):
                total += 1
                if (ast.get_docstring(node) is not None and 
                    ast.get_docstring(node).strip()):
                    documented += 1
                
                # Check methods inside classes
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        total += 1
                        if (ast.get_docstring(item) is not None and 
                            ast.get_docstring(item).strip()):
                            documented += 1
        
        coverage = (documented / total * 100) if total > 0 else 0
        return documented, total, coverage
        
    except Exception as e:
        print(f"Error processing {module_path}: {e}")
        return 0, 0, 0


def get_missing_docstrings(module_path: str) -> List[str]:
    """Get list of functions/classes missing docstrings.
    
    Args:
        module_path: Path to the Python file
        
    Returns:
        List of missing docstring items
    """
    missing = []
    
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            # Check functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if (ast.get_docstring(node) is None or 
                    not ast.get_docstring(node).strip()):
                    missing.append(f"Function: {node.name}")
            
            # Check classes
            elif isinstance(node, ast.ClassDef):
                if (ast.get_docstring(node) is None or 
                    not ast.get_docstring(node).strip()):
                    missing.append(f"Class: {node.name}")
                
                # Check methods inside classes
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if (ast.get_docstring(item) is None or 
                            not ast.get_docstring(item).strip()):
                            missing.append(f"Method: {node.name}.{item.name}")
        
        return missing
        
    except Exception as e:
        print(f"Error processing {module_path}: {e}")
        return []


def main():
    """Main function to check docstring coverage."""
    
    # Files to check
    files_to_check = [
        "app.py",
        "build_utils.py"
    ]
    
    print("=" * 60)
    print("DOCSTRING COVERAGE REPORT")
    print("=" * 60)
    
    total_documented = 0
    total_items = 0
    
    for file_path in files_to_check:
        if Path(file_path).exists():
            documented, total, coverage = get_docstring_coverage(file_path)
            total_documented += documented
            total_items += total
            
            print(f"\n📄 {file_path}")
            print(f"   Documented: {documented}/{total}")
            print(f"   Coverage: {coverage:.1f}%")
            
            # Show missing docstrings if any
            missing = get_missing_docstrings(file_path)
            if missing and len(missing) <= 10:  # Show first 10 missing items
                print(f"   Missing docstrings:")
                for item in missing[:10]:
                    print(f"     - {item}")
                if len(missing) > 10:
                    print(f"     ... and {len(missing) - 10} more")
            elif missing:
                print(f"   Missing docstrings: {len(missing)} items")
        else:
            print(f"\n❌ {file_path} - File not found")
    
    # Overall coverage
    overall_coverage = (total_documented / total_items * 100) if total_items > 0 else 0
    print(f"\n{'='*60}")
    print(f"OVERALL COVERAGE: {total_documented}/{total_items} ({overall_coverage:.1f}%)")
    print(f"{'='*60}")
    
    # Rating
    if overall_coverage >= 90:
        print("🌟 EXCELLENT documentation!")
    elif overall_coverage >= 75:
        print("✅ GOOD documentation!")
    elif overall_coverage >= 50:
        print("⚠️  FAIR documentation - consider improving")
    else:
        print("❌ POOR documentation - needs significant improvement")


if __name__ == "__main__":
    main()
