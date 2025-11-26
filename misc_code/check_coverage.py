#!/usr/bin/env python3
"""
Comprehensive code coverage checker for FOAMFlask project.
"""

import os
import sys
import subprocess
import webbrowser
from pathlib import Path


def run_coverage_analysis():
    """Run coverage analysis on the project."""
    
    print("=" * 60)
    print("CODE COVERAGE ANALYSIS")
    print("=" * 60)
    
    # Check if coverage is installed
    try:
        subprocess.run([sys.executable, "-m", "coverage", "--version"], 
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ coverage.py not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "coverage"], check=True)
        print("✅ coverage.py installed successfully!")
    
    # Check if we have test files
    test_files = list(Path(".").glob("**/test_*.py"))
    if not test_files:
        print("⚠️  No test files found (test_*.py)")
        print("Creating a basic test file...")
        
        # Create a basic test file
        basic_test = '''#!/usr/bin/env python3
"""
Basic test file for coverage demonstration.
"""

def test_imports():
    """Test that we can import basic modules."""
    import os
    import sys
    assert os is not None
    assert sys is not None

if __name__ == "__main__":
    test_imports()
    print("✅ Basic test passed!")
'''
        
        with open("test_basic_coverage.py", "w") as f:
            f.write(basic_test)
        
        test_files = ["test_basic_coverage.py"]
        print("✅ Created test_basic_coverage.py")
    
    print(f"\n📊 Found {len(test_files)} test file(s):")
    for test_file in test_files:
        print(f"   - {test_file}")
    
    # Run coverage
    print(f"\n🔄 Running coverage analysis...")
    
    try:
        # Run coverage on all test files
        for test_file in test_files:
            print(f"   Running: {test_file}")
            result = subprocess.run([
                sys.executable, "-m", "coverage", "run", "-a", str(test_file)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"   ❌ Error running {test_file}: {result.stderr}")
            else:
                print(f"   ✅ {test_file} completed")
        
        # Generate coverage report
        print(f"\n📈 Generating coverage report...")
        result = subprocess.run([
            sys.executable, "-m", "coverage", "report"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Warnings:", result.stderr)
        
        # Generate HTML report
        print(f"\n🌐 Generating HTML coverage report...")
        result = subprocess.run([
            sys.executable, "-m", "coverage", "html"
        ], capture_output=True, text=True)
        
        if "Wrote HTML report" in result.stdout:
            html_dir = "htmlcov"
            html_index = os.path.join(html_dir, "index.html")
            
            print(f"✅ HTML report generated: {html_index}")
            
            # Ask if user wants to open the report
            try:
                choice = input("\n🌍 Open HTML coverage report in browser? (y/n): ").lower().strip()
                if choice in ['y', 'yes']:
                    webbrowser.open(f"file://{os.path.abspath(html_index)}")
                    print("🌐 Opened coverage report in browser")
            except KeyboardInterrupt:
                print("\n👋 Skipping browser opening")
        
        # Show coverage summary
        print(f"\n📋 Coverage Summary:")
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if '%' in line and 'TOTAL' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        coverage_pct = parts[3]
                        print(f"   Total Coverage: {coverage_pct}")
                        
                        # Rating
                        pct_num = float(coverage_pct.rstrip('%'))
                        if pct_num >= 90:
                            print("   🌟 EXCELLENT coverage!")
                        elif pct_num >= 75:
                            print("   ✅ GOOD coverage!")
                        elif pct_num >= 50:
                            print("   ⚠️  FAIR coverage - consider improving")
                        else:
                            print("   ❌ POOR coverage - needs significant improvement")
                        break
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during coverage analysis: {e}")
        return False
    
    return True


def show_coverage_commands():
    """Show useful coverage commands."""
    print(f"\n🛠️  Useful Coverage Commands:")
    print(f"   Run coverage:          python -m coverage run test_file.py")
    print(f"   Show report:           python -m coverage report")
    print(f"   HTML report:           python -m coverage html")
    print(f"   Terminal report:       python -m coverage report -m")
    print(f"   Missing lines only:    python -m coverage report --skip-covered")
    print(f"   Combine coverage:      python -m coverage combine")
    print(f"   Clear coverage data:   python -m coverage erase")


def main():
    """Main function."""
    
    print("🎯 FOAMFlask Code Coverage Checker")
    
    # Check if we're in the right directory
    if not Path("app.py").exists():
        print("❌ app.py not found. Please run from the FOAMFlask root directory.")
        return
    
    # Run coverage analysis
    success = run_coverage_analysis()
    
    if success:
        show_coverage_commands()
    
    print(f"\n{'='*60}")
    print("🎯 Coverage analysis complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
