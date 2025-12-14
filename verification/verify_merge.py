from playwright.sync_api import sync_playwright
import time

def verify():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # We need to start the app first. I'll do that in a separate command.
        # Assuming app is running on port 5000
        try:
            page.goto('http://localhost:5000', timeout=5000)
        except Exception as e:
            print(f'Failed to load page: {e}')
            return

        # Wait for loading
        try:
            # Wait for modal to appear first (maybe) or just wait for it to disappear
            # Since docker is failing, it might stay or show error.
            # We just want to see the UI behind it or the error.
            time.sleep(2)
        except:
            pass

        # Check if tabs exist
        page.screenshot(path='verification/landing.png')

        # Click Geometry tab
        try:
            page.click('#nav-geometry', timeout=2000)
            time.sleep(1)
            page.screenshot(path='verification/geometry_tab.png')
        except:
            print("Could not click geometry tab")

        # Click Meshing tab
        try:
            page.click('#nav-meshing', timeout=2000)
            time.sleep(1)
            # Check for new controls
            page.screenshot(path='verification/meshing_tab.png')
        except:
            print("Could not click meshing tab")

        browser.close()

if __name__ == '__main__':
    verify()
