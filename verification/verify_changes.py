from playwright.sync_api import sync_playwright
import time

def verify_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the app
        page.goto("http://localhost:5000")

        # Wait for potential startup modal and remove it if present (since backend checks might fail in this env)
        try:
            page.wait_for_selector("#startup-modal", timeout=5000)
            # Remove the modal from DOM to interact with page
            page.evaluate("document.getElementById('startup-modal').remove()")
        except:
            pass

        # Verify initial page load
        page.screenshot(path="verification/initial_load.png")

        # Test navigation to geometry page (where uploads happen)
        # Click on 'Geometry' in nav
        page.click("#nav-geometry")
        time.sleep(1)
        page.screenshot(path="verification/geometry_page.png")

        # Test navigation to meshing page
        page.click("#nav-meshing")
        time.sleep(1)
        page.screenshot(path="verification/meshing_page.png")

        browser.close()

if __name__ == "__main__":
    verify_frontend()
