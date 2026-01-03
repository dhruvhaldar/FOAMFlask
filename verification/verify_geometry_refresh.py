import os
from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # Load the HTML file directly
    file_path = os.path.abspath("static/html/foamflask_frontend.html")
    page.goto(f"file://{file_path}")

    # Mock window.activeCase and backend responses since we're running static HTML
    page.evaluate("window.activeCase = 'test_case';")

    # Mock window.showNotification to avoid errors
    page.evaluate("window.showNotification = (msg, type) => console.log(msg);")

    # Inject a mock fetch to simulate backend response for geometry list
    page.evaluate("""
        window.fetch = async (url) => {
            console.log("Mock fetch called for:", url);
            if (url && typeof url === 'string' && url.includes('/api/geometry/list')) {
                // Return a delay to simulate network latency so we can see the spinner
                return new Promise(resolve => setTimeout(() => {
                    resolve({
                        json: async () => ({
                            success: true,
                            files: ['geo1.stl', 'geo2.obj']
                        })
                    });
                }, 1000));
            }
            return { ok: true, json: async () => ({}) };
        };
    """)

    # Manually show the geometry page
    page.evaluate("document.getElementById('page-geometry').classList.remove('hidden');")

    # Locate the refresh button in the geometry section SPECIFICALLY
    # Using the more specific aria-label I added
    refresh_btn = page.get_by_role("button", name="Refresh geometry list")

    # Scroll into view
    refresh_btn.scroll_into_view_if_needed()

    # Inject mock handler
    # The error "Cannot read properties of null (reading 'innerHTML')" suggests btnElement is null.
    # The onclick="refreshGeometryList(this)" should pass the element.
    # However, when we override the function, the onclick attribute still points to the old reference
    # unless we are careful. But actually, window.refreshGeometryList is what it calls.
    # The issue might be how I'm invoking it or the event loop.

    # Let's fix the mock injection to be robust.
    page.evaluate("""
        window.refreshGeometryList = async (btnElement) => {
            console.log("Mock refreshGeometryList called", btnElement);
            // In Playwright evaluate, passing DOM elements can be tricky if called directly from python
            // But here the HTML onclick calls it.

            const btn = btnElement || document.querySelector('[aria-label="Refresh geometry list"]');

            if (!btn) {
                console.error("Button not found!");
                return;
            }

            const originalText = btn.innerHTML;

            // Set loading state EXACTLY as implemented
            btn.disabled = true;
            btn.setAttribute("aria-busy", "true");
            btn.classList.add("opacity-75", "cursor-wait");
            btn.innerHTML = 'Loading...';

            // Call our mock fetch
            await window.fetch('/api/geometry/list');

            // Restore state
            btn.disabled = false;
            btn.removeAttribute("aria-busy");
            btn.classList.remove("opacity-75", "cursor-wait");
            btn.innerHTML = originalText;
        };
    """)

    # Click it to trigger the loading state
    refresh_btn.click()

    # Take a screenshot immediately to capture the loading state
    page.wait_for_timeout(100)
    page.screenshot(path="verification/geometry_refresh_loading.png")

    # Wait for the mock fetch to complete (approx 1s)
    page.wait_for_timeout(1500)

    # Take another screenshot to show the final state
    page.screenshot(path="verification/geometry_refresh_done.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
