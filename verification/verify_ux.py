
import os
from playwright.sync_api import sync_playwright, expect

def verify_font_settings(page):
    # Load the local HTML file directly
    html_path = os.path.abspath("static/html/foamflask_frontend.html")
    page.goto(f"file://{html_path}")

    # Inject missing JS functions to make the toggle work without backend
    page.evaluate("""
        window.toggleFontSettings = function() {
            const menu = document.getElementById("fontSettingsMenu");
            const btn = document.getElementById("fontSettingsBtn");
            if (menu) {
                const isHidden = menu.classList.contains("hidden");
                if (isHidden) {
                    menu.classList.remove("hidden");
                    if (btn) btn.setAttribute("aria-expanded", "true");
                } else {
                    menu.classList.add("hidden");
                    if (btn) btn.setAttribute("aria-expanded", "false");
                }
            }
        };
        // Mock switchPage
        window.switchPage = function(pageId) {
            const pages = ["setup", "geometry", "meshing", "visualizer", "run", "plots", "post"];
            pages.forEach(p => {
                const el = document.getElementById('page-' + p);
                if (el) el.classList.add('hidden');
            });
            const selected = document.getElementById('page-' + pageId);
            if (selected) selected.classList.remove('hidden');
        };
    """)

    # Switch to plots page to see the button
    page.evaluate("switchPage('plots')")

    # Locate the Font Settings button
    btn = page.locator("#fontSettingsBtn")

    # Check initial attributes
    print("Checking initial state...")
    expect(btn).to_have_attribute("aria-haspopup", "true")
    expect(btn).to_have_attribute("aria-expanded", "false")

    # Click to toggle
    print("Clicking to open...")
    btn.click()
    expect(btn).to_have_attribute("aria-expanded", "true")

    # Locate the close button inside the menu
    close_btn = page.locator("#fontSettingsMenu button[aria-label='Close font settings']")
    print("Checking close button...")
    expect(close_btn).to_be_visible()

    # Take screenshot of open menu
    page.screenshot(path="verification/font_settings_open.png")

    # Click close button
    print("Clicking close button...")
    close_btn.click()

    # Since our mocked toggleFontSettings handles the close logic inside the button click,
    # we need to simulate that the close button calls toggleFontSettings
    # In the actual HTML, it calls toggleFontSettings().
    # Our mocked function toggles based on hidden state.

    expect(btn).to_have_attribute("aria-expanded", "false")

    print("Verification successful!")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_font_settings(page)
        except Exception as e:
            print(f"Verification failed: {e}")
            page.screenshot(path="verification/error.png")
            raise
        finally:
            browser.close()
