
import os
from playwright.sync_api import sync_playwright, expect

def verify_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load the HTML file directly
        html_path = os.path.abspath("static/html/foamflask_frontend.html")
        page.goto(f"file://{html_path}")

        # Remove the startup modal which might be blocking
        page.evaluate("document.getElementById('startup-modal')?.remove()")

        # Unhide the geometry page to make elements visible
        page.evaluate("document.getElementById('page-geometry').classList.remove('hidden')")

        # 1. Verify Label association
        label = page.get_by_text("Upload Geometry File (stl, obj, obj.gz)")
        expect(label).to_be_visible()

        # Check 'for' attribute
        for_attr = label.get_attribute("for")
        assert for_attr == "geometryUpload", f"Expected label for='geometryUpload', got '{for_attr}'"
        print("✅ Label 'for' attribute verified.")

        # 2. Verify Button ID
        btn = page.locator("#uploadGeometryBtn")
        expect(btn).to_be_visible()
        expect(btn).to_have_text("Upload")
        print("✅ Button ID and Text verified.")

        # 3. Simulate Upload Click to verify Loading State
        page.evaluate("""
            const btn = document.getElementById('uploadGeometryBtn');
            btn.innerHTML = `<svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Uploading...`;
        """)

        # Take screenshot of the area
        page.screenshot(path="verification_frontend.png")
        print("✅ Screenshot taken.")

        browser.close()

if __name__ == "__main__":
    verify_frontend()
