from playwright.sync_api import sync_playwright
import time

def verify_tooltips():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            print("Navigating...")
            # Use 127.0.0.1 and wait for domcontentloaded
            page.goto("http://127.0.0.1:5000", wait_until="domcontentloaded", timeout=60000)
            print("Page loaded.")

            # 1. Mobile Menu Button
            page.set_viewport_size({"width": 375, "height": 667})
            menu_btn = page.locator("#mobile-menu-btn")
            title = menu_btn.get_attribute("title")
            print(f"Mobile Menu Title: {title}")
            assert title == "Toggle menu", f"Expected 'Toggle menu', got '{title}'"

            # Reset viewport
            page.set_viewport_size({"width": 1280, "height": 720})

            # 2. Notification Close Button
            page.evaluate("window.showNotification('Test Notification', 'info')")
            close_btn = page.locator(".notification .close-btn").first
            title = close_btn.get_attribute("title")
            print(f"Notification Close Title: {title}")
            assert title == "Close notification", f"Expected 'Close notification', got '{title}'"

            # 3. Font Settings Close Button
            page.evaluate("window.switchPage('plots')")
            page.evaluate("window.toggleFontSettings()")
            font_close_btn = page.locator("#fontSettingsMenu button[aria-label='Close font settings']")
            title = font_close_btn.get_attribute("title")
            print(f"Font Close Title: {title}")
            assert title == "Close font settings", f"Expected 'Close font settings', got '{title}'"

            # 4. Post Processing Back Button
            page.evaluate("window.switchPage('post')")
            page.evaluate("document.getElementById('post-contour-view').classList.remove('hidden')")
            back_btn = page.locator("#post-contour-view button[aria-label='Back to selection']")
            title = back_btn.get_attribute("title")
            print(f"Post Back Title: {title}")
            assert title == "Back to selection", f"Expected 'Back to selection', got '{title}'"

            # Screenshot of Post View to confirm visibility
            page.screenshot(path="verification/verification.png")
            print("Verification successful!")

        except Exception as e:
            print(f"Error: {e}")
            try:
                page.screenshot(path="verification/error.png")
            except:
                pass
        finally:
            browser.close()

if __name__ == "__main__":
    verify_tooltips()
