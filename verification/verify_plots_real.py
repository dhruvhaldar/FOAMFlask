import logging
from playwright.sync_api import sync_playwright, expect
import time
import threading
import sys
import os
import requests

def run_mock_app():
    # Run the mock app
    import subprocess
    return subprocess.Popen([sys.executable, "verification/mock_app.py"])

def verify_plots():
    server_process = run_mock_app()

    # Wait for server
    for _ in range(10):
        try:
            requests.get("http://localhost:5000")
            break
        except:
            time.sleep(1)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Go to the main page
            page.goto("http://localhost:5000")

            # The mock app returns startup status completed, so modal should close or not block
            # But let's verify
            try:
                page.wait_for_selector("#startup-modal", state="hidden", timeout=2000)
            except:
                page.evaluate("document.getElementById('startup-modal')?.remove()")

            # Navigate to Plots tab
            # Ensure the nav button is clickable
            page.wait_for_selector("#nav-plots")
            page.click("#nav-plots")

            # Wait for plot containers to be visible
            page.wait_for_selector("#plotsContainer")

            # Select a mock tutorial/case to trigger data fetch
            # The JS requires a tutorial to be selected for updates
            page.evaluate("""() => {
               const select = document.getElementById('tutorialSelect');
               const opt = document.createElement('option');
               opt.value = 'test_tutorial';
               opt.text = 'test_tutorial';
               select.add(opt);
               select.value = 'test_tutorial';
               select.dispatchEvent(new Event('change'));
            }""")

            # Trigger updatePlots manually or wait for interval
            # The frontend calls startPlotUpdates when tab is switched to plots

            # Wait for Plotly to render
            # Plotly adds 'js-plotly-plot' class
            page.wait_for_selector("#pressure-plot .js-plotly-plot", timeout=5000)
            page.wait_for_selector("#velocity-plot .js-plotly-plot", timeout=5000)

            # Check trace type for 'pressure-plot'
            # We access the plotly object attached to the DOM element
            trace_type = page.evaluate("""() => {
                const el = document.getElementById('pressure-plot');
                return el.data && el.data[0] ? el.data[0].type : 'unknown';
            }""")

            print(f"Pressure Plot Trace Type: {trace_type}")

            if trace_type != 'scattergl':
                print(f"FAILURE: Expected 'scattergl', got '{trace_type}'")
                sys.exit(1)
            else:
                print("SUCCESS: Pressure plot is using scattergl")

            # Check trace type for 'velocity-plot'
            trace_type_vel = page.evaluate("""() => {
                const el = document.getElementById('velocity-plot');
                return el.data && el.data[0] ? el.data[0].type : 'unknown';
            }""")

            print(f"Velocity Plot Trace Type: {trace_type_vel}")

            if trace_type_vel != 'scattergl':
                 print(f"FAILURE: Expected 'scattergl', got '{trace_type_vel}'")
                 sys.exit(1)

            # Take screenshot
            page.screenshot(path="verification/plots_verification.png")
            print("Screenshot saved to verification/plots_verification.png")

    except Exception as e:
        print(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        server_process.terminate()

if __name__ == "__main__":
    verify_plots()
