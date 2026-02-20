from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Mock startup status to avoid infinite polling/modal
    page.route("**/api/startup_status", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='{"status": "completed", "message": "Ready"}'
    ))

    # Mock other APIs to prevent errors in console
    page.route("**/get_case_root", lambda route: route.fulfill(json={"caseDir": "/tmp"}))
    page.route("**/get_docker_config", lambda route: route.fulfill(json={"dockerImage": "img", "openfoamVersion": "v1"}))
    page.route("**/api/cases/list", lambda route: route.fulfill(json={"cases": ["test_case"]}))
    page.route("**/api/runs", lambda route: route.fulfill(json={"runs": []}))

    page.goto("http://localhost:8000/index.html")

    # Select a case to unlock protected pages
    page.evaluate("window.selectCase('test_case')")

    # Click 'Run/Log' tab
    page.click("#nav-run")

    # Wait for output to be visible
    output = page.locator("#output")
    expect(output).to_be_visible()

    # Check for placeholder
    placeholder = output.locator(".output-placeholder")
    expect(placeholder).to_be_visible()
    # Use loose match for text as there might be whitespace
    expect(placeholder).to_contain_text("Ready for output...")

    # Take screenshot of the output div
    output.screenshot(path="verification/console_placeholder.png")
    print("Screenshot saved to verification/console_placeholder.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
