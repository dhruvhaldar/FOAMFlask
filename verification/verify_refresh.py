
import os
from playwright.sync_api import sync_playwright, expect

def verify_refresh_button():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load the HTML file directly
        file_url = f"file://{os.path.abspath('static/html/foamflask_frontend.html')}"
        page.goto(file_url)

        # Mock the global objects and functions expected by the frontend
        page.evaluate("""
            window.activeCase = 'test_case';
            window.refreshPostList = async (btn) => {
                // Simulate loading state
                if (btn) {
                   const original = btn.innerHTML;
                   btn.disabled = true;
                   btn.innerHTML = 'Loading...';
                   await new Promise(r => setTimeout(r, 500));
                   btn.disabled = false;
                   btn.innerHTML = original;
                }
            };
        """)

        # Navigate to Post tab (simulate switchPage logic since we can't run full JS modules easily in file://)
        # We manually unhide the section
        page.evaluate("""
            document.getElementById('page-setup').classList.add('hidden');
            document.getElementById('page-post').classList.remove('hidden');
        """)

        # Wait for the element to be visible
        btn = page.locator("#refreshPostVTKBtn")
        expect(btn).to_be_visible()

        # Take screenshot of the Post Processing section
        page.locator("#page-post").screenshot(path="verification/post_tab_refresh_btn.png")

        print("Screenshot saved to verification/post_tab_refresh_btn.png")
        browser.close()

if __name__ == "__main__":
    verify_refresh_button()
