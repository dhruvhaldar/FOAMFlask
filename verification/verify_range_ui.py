from playwright.sync_api import sync_playwright
import time

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # Mock endpoints to bypass backend logic
    page.route("/api/startup_status", lambda route: route.fulfill(json={"status": "completed", "message": "Ready"}))
    page.route("/get_case_root", lambda route: route.fulfill(json={"caseDir": "/tmp/test"}))
    page.route("/get_docker_config", lambda route: route.fulfill(json={"dockerImage": "test", "openfoamVersion": "v2206"}))
    page.route("/api/cases/list", lambda route: route.fulfill(json={"cases": ["test_case"]}))
    page.route("/api/available_meshes", lambda route: route.fulfill(json={"meshes": []})) # Mock empty mesh list

    # Go to app
    try:
        page.goto("http://127.0.0.1:5000", timeout=10000)
    except Exception as e:
        print(f"Failed to load page: {e}")
        # Try once more
        time.sleep(2)
        page.goto("http://127.0.0.1:5000")

    # Wait for page to load (setup page is default)
    # Remove startup modal if it appears (though mocked status should prevent it)
    page.evaluate("document.getElementById('startup-modal')?.remove()")

    # Navigate to Post page manually via JS to skip checks if any
    page.evaluate("switchPage('post')")

    # Wait for Post page
    page.wait_for_selector("#page-post:not(.hidden)")

    # Click 'Contour' button in Landing View
    # The contour button is the first one in #post-landing-view
    # We can use text locator to be safe
    page.locator("#post-landing-view button", has_text="Contour").click()

    # Wait for Contour View
    page.wait_for_selector("#post-contour-view:not(.hidden)")

    # Screenshot the Range Selection area (specifically the fieldset)
    # The fieldset doesn't have an ID, but it contains "Scalar Range" legend
    fieldset = page.locator("fieldset", has_text="Scalar Range")

    # Wait for it to be visible
    fieldset.wait_for(state="visible")

    # Screenshot
    fieldset.screenshot(path="verification/range_ui.png")

    # Also screenshot the whole sidebar for context
    page.locator("#post-contour-view > div > div:first-child").screenshot(path="verification/contour_sidebar.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
