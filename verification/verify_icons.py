
import os
from playwright.sync_api import sync_playwright

def verify_icons():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load the local HTML file
        file_path = os.path.abspath("static/html/foamflask_frontend.html")
        page.goto(f"file://{file_path}")

        # Mock necessary globals to avoid errors
        page.evaluate("""
            window.Plotly = { react: () => {} };
            window.startPlotUpdates = () => {};
        """)

        # Simulate switching to the 'run' page
        # Since logic is in TS and might not be fully loaded/functional in this static context without a server,
        # we will manually unhide the run page and hide others using DOM manipulation
        page.evaluate("""
            document.querySelectorAll('.page').forEach(el => el.classList.add('hidden'));
            document.getElementById('page-run').classList.remove('hidden');
        """)

        # Wait for the buttons to be visible
        page.wait_for_selector("#runAllrunBtn")

        # Take a screenshot of the Run Commands section
        # We target the parent container of the buttons
        # The buttons are in a div with class "my-4" inside #page-run
        # Let's target #page-run

        page.screenshot(path="verification/verification.png", full_page=True)
        print("Screenshot saved to verification/verification.png")

        browser.close()

if __name__ == "__main__":
    verify_icons()
