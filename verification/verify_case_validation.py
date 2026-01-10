import http.server
import socketserver
import threading
import time
import os
from playwright.sync_api import sync_playwright, expect

# --- 1. Set up a simple static file server ---
PORT = 8000
DIRECTORY = "."

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    # Suppress log messages
    def log_message(self, format, *args):
        pass

def start_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()

# Start server in a background thread
server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()

# Give server time to start
time.sleep(2)

def run_verification():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Navigate to the frontend HTML served by our local server
            # We need to target the HTML file specifically
            page.goto(f"http://localhost:{PORT}/static/html/foamflask_frontend.html")

            # Mock window.switchCaseCreationTab since it might depend on other JS loading
            # But we are testing the static HTML attribute for validation.
            # However, the JS file also has logic.
            # The HTML has Jinja2 templates {{ url_for ... }} which won't render correctly.
            # But the browser should just ignore them or show them as text.
            # We are interested in #newCaseName input.

            # Wait for content to load (the body content)
            page.wait_for_selector("#main-content")

            # Make the setup page visible manually since the JS normally handles it
            page.evaluate("document.getElementById('page-setup').classList.remove('hidden')")

            # Locate the input
            input_locator = page.locator("#newCaseName")

            # Check for pattern attribute
            pattern = input_locator.get_attribute("pattern")
            print(f"Pattern attribute: {pattern}")
            assert pattern == "^[a-zA-Z0-9_-]+$"

            # Check for title attribute
            title = input_locator.get_attribute("title")
            print(f"Title attribute: {title}")
            assert "Alphanumeric characters" in title

            # Focus the input to show it active
            input_locator.focus()

            # Type an invalid character to trigger browser validation styling (if :invalid is used)
            # Or just type something to show it's focused
            input_locator.fill("invalid case name with spaces")

            # Check validity via JS
            is_valid = page.evaluate("document.getElementById('newCaseName').checkValidity()")
            print(f"Is valid (should be False): {is_valid}")

            # Take screenshot of the input area
            # We want to capture the form area
            page.locator("#tab-content-create").screenshot(path="verification/case_validation.png")
            print("Screenshot saved to verification/case_validation.png")

        except Exception as e:
            print(f"Verification failed: {e}")
            page.screenshot(path="verification/error.png")
        finally:
            browser.close()

if __name__ == "__main__":
    run_verification()
