
import logging
from playwright.sync_api import sync_playwright, expect
import time
import threading
import sys
import os

# Ensure backend path is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app, socketio

def run_app():
    # Disable CSRF for testing
    app.config['WTF_CSRF_ENABLED'] = False
    socketio.run(app, port=5000, debug=False, use_reloader=False)

def verify_frontend():
    # Start the app in a separate thread
    server_thread = threading.Thread(target=run_app)
    server_thread.daemon = True
    server_thread.start()

    # Wait for server to start
    time.sleep(5)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Go to the main page
            page.goto("http://localhost:5000")

            # Wait for the page to load (check for a known element)
            # The app has a #startup-modal that might block interaction initially,
            # but in this mock environment without Docker, it might fail or persist.
            # We can try to remove it if it exists.

            # Check if startup modal is present
            try:
                page.wait_for_selector("#startup-modal", timeout=5000)
                # Remove it manually to proceed
                page.evaluate("document.getElementById('startup-modal')?.remove()")
            except:
                pass # Modal didn't appear or wasn't found, which is fine

            # Navigate to Plots tab
            page.click("#nav-plots")

            # Wait for plots container
            page.wait_for_selector("#plotsContainer")

            # Check if Plotly plots are rendered
            # We look for the "js-plotly-plot" class which Plotly adds
            expect(page.locator("#pressure-plot .js-plotly-plot")).to_be_visible(timeout=10000)

            # Verify that the trace type is indeed scattergl?
            # This is hard to verify visually or via DOM class, as scattergl renders to canvas.
            # However, we can check the internal data of the plot via page.evaluate

            # Get the trace type of the pressure plot
            trace_type = page.evaluate("""() => {
                const el = document.getElementById('pressure-plot');
                return el.data[0].type;
            }""")

            print(f"Pressure Plot Trace Type: {trace_type}")

            if trace_type != 'scattergl':
                print("Error: Trace type is not scattergl!")
                # Don't fail the script yet, let's take a screenshot first

            # Take a screenshot of the plots page
            page.screenshot(path="verification/plots_verification.png")

        except Exception as e:
            print(f"Verification failed: {e}")
            page.screenshot(path="verification/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    verify_frontend()
