from playwright.sync_api import sync_playwright, expect
import os
import re

def test_refresh_buttons():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load the local HTML file directly
        cwd = os.getcwd()
        file_url = f"file://{cwd}/static/html/foamflask_frontend.html"
        page.goto(file_url)

        # 1. Verify Refresh Case List Button
        case_btn = page.locator("#refreshCaseListBtn")
        expect(case_btn).to_be_visible()
        # Check aria-label
        expect(case_btn).to_have_attribute("aria-label", "Refresh case list")

        # 2. Verify Refresh Mesh List Button
        mesh_btn = page.locator("#refreshMeshListBtn")

        # Check class using regex to ensure flex, items-center, gap-1 are present
        expect(mesh_btn).to_have_class(re.compile(r"flex"))
        expect(mesh_btn).to_have_class(re.compile(r"items-center"))
        expect(mesh_btn).to_have_class(re.compile(r"gap-1"))

        # Check aria-label
        expect(mesh_btn).to_have_attribute("aria-label", "Refresh mesh list")

        # Make Visualizer page visible to screenshot
        page.evaluate("document.getElementById('page-visualizer').classList.remove('hidden')")
        page.evaluate("document.getElementById('page-setup').classList.add('hidden')")

        # Take screenshot of the button area
        # We screenshot the container to see context
        container = page.locator("#meshActionButtons")
        container.screenshot(path="verification/refresh_mesh_btn.png")

        print("Verification passed!")
        browser.close()

if __name__ == "__main__":
    test_refresh_buttons()
