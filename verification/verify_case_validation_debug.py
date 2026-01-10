import http.server
import socketserver
import threading
import time
import os
from playwright.sync_api import sync_playwright, expect

# --- 1. Set up a simple static file server ---
PORT = 8002
DIRECTORY = "."

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    # Suppress log messages
    def log_message(self, format, *args):
        pass

def start_server():
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Serving at port {PORT}")
            httpd.serve_forever()
    except OSError:
        pass # Port likely in use

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
            page.goto(f"http://localhost:{PORT}/static/html/foamflask_frontend.html")

            # Wait for content
            page.wait_for_selector("#main-content")

            # Make the setup page visible
            page.evaluate("document.getElementById('page-setup').classList.remove('hidden')")

            # Locate the input
            input_locator = page.locator("#newCaseName")

            # Check for pattern attribute
            pattern = input_locator.get_attribute("pattern")
            print(f"Pattern attribute: {pattern}")

            # Type an invalid character to trigger browser validation state
            input_locator.focus(); page.keyboard.type("invalid case name") # has spaces

            # We need to blur or submit to trigger validity check sometimes?
            # Or just check property
            is_valid = page.evaluate("document.getElementById('newCaseName').checkValidity()")
            # "invalid case name" has spaces. The pattern ^[a-zA-Z0-9_-]+$ does NOT match spaces.
            # So checkValidity() MUST be false.

            print(f"Value: '{input_locator.input_value()}'")
            print(f"Is valid: {is_valid}")

            # If still true, let's debug the regex
            # JS regex test:
            js_regex_test = page.evaluate("new RegExp('^[a-zA-Z0-9_-]+$').test('invalid case name')")
            print(f"JS Regex test: {js_regex_test}")

            # Take screenshot of the input area with invalid data
            input_locator.focus()
            page.locator("#tab-content-create").screenshot(path="verification/case_validation_v2.png")
            print("Screenshot saved to verification/case_validation_v2.png")

        except Exception as e:
            print(f"Verification failed: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    run_verification()
