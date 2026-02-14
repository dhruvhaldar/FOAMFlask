from playwright.sync_api import sync_playwright, expect

def verify_accesskeys():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("http://127.0.0.1:5000/")

            # Wait for navbar to be visible
            expect(page.locator("#navbar")).to_be_visible()

            # Remove the startup modal if it appears (it blocks interaction)
            # We wait a bit to see if it appears
            try:
                page.wait_for_selector("#startup-modal", timeout=2000)
                page.evaluate("document.getElementById('startup-modal').remove()")
            except:
                pass # Modal didn't appear

            # Define expected attributes
            expected_keys = {
                "nav-setup": ("s", "Setup (AccessKey: s)"),
                "nav-geometry": ("g", "Geometry (AccessKey: g)"),
                "nav-meshing": ("m", "Meshing (AccessKey: m)"),
                "nav-visualizer": ("v", "Visualizer (AccessKey: v)"),
                "nav-run": ("r", "Run/Log (AccessKey: r)"),
                "nav-plots": ("p", "Plots (AccessKey: p)"),
                "nav-post": ("o", "Post (AccessKey: o)"),
            }

            for id, (key, title) in expected_keys.items():
                btn = page.locator(f"#{id}")
                expect(btn).to_have_attribute("accesskey", key)
                expect(btn).to_have_attribute("title", title)
                print(f"Verified {id}: accesskey='{key}', title='{title}'")

            page.screenshot(path="verification_accesskeys.png")
            print("Verification successful!")

        except Exception as e:
            print(f"Verification failed: {e}")
            page.screenshot(path="verification_failed.png")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    verify_accesskeys()
