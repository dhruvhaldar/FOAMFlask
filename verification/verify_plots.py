from playwright.sync_api import sync_playwright

def verify_plot_updates():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the app
        page.goto("http://localhost:5000")

        # Wait for initialization (startup modal to disappear)
        try:
            page.wait_for_selector("#startup-modal", state="hidden", timeout=10000)
        except:
             # If backend is slow/failing (no docker), manually hide it to verify UI structure
            page.evaluate("document.getElementById('startup-modal')?.remove()")

        # Switch to plots tab
        page.click("#nav-plots")

        # Verify plots container is visible
        page.wait_for_selector("#plotsContainer", state="visible")

        # Click toggle aero plots button
        # First ensure the button is visible
        page.wait_for_selector("#toggleAeroBtn", state="visible")
        page.click("#toggleAeroBtn")

        # Wait a bit for potential network requests
        page.wait_for_timeout(2000)

        # Take screenshot
        page.screenshot(path="verification/plots_verification.png")

        browser.close()

if __name__ == "__main__":
    verify_plot_updates()
