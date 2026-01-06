from playwright.sync_api import sync_playwright

def verify_ux_improvements():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load the HTML file directly
        import os
        cwd = os.getcwd()
        page.goto(f"file://{cwd}/static/html/foamflask_frontend.html")

        # 1. Verify "Active Case" select has focus ring class
        case_select = page.locator("#caseSelect")
        # We can't easily check for Tailwind classes applying styles without CSS loaded (CDN),
        # but we can check the class attribute contains our added classes.

        # We need to simulate the environment since we are loading file://
        # Inject the CSS to make sure we can see the focus ring if we were to take a screenshot
        # But primarily we want to verify the markup changes.

        classes = case_select.get_attribute("class")
        print(f"Case Select Classes: {classes}")
        if "focus:ring-2" in classes and "focus:ring-cyan-500" in classes:
            print("PASS: Case Select has focus classes")
        else:
            print("FAIL: Case Select missing focus classes")

        # 2. Verify BlockMesh inputs have focus ring
        page.click("#nav-meshing")

        # We need to open the blockMesh section
        # The toggleSection function relies on JS which might not run correctly without modules
        # but the HTML structure is there.
        # Let's just find the element and check classes.

        bm_min = page.locator("#bmMin")
        bm_classes = bm_min.get_attribute("class")
        print(f"BlockMesh Min Classes: {bm_classes}")
        if "focus:ring-2" in bm_classes:
            print("PASS: BlockMesh Min has focus classes")
        else:
             print("FAIL: BlockMesh Min missing focus classes")

        # 3. Verify Auto-fill button has focus ring and onclick
        # Note: the button text is "Auto-fill from selected Geometry"
        auto_fill_btn = page.locator("button:has-text('Auto-fill from selected Geometry')")
        btn_classes = auto_fill_btn.get_attribute("class")
        print(f"Auto-fill Btn Classes: {btn_classes}")

        onclick = auto_fill_btn.get_attribute("onclick")
        print(f"Auto-fill Btn Onclick: {onclick}")

        if "fillBoundsFromGeometry(this)" in onclick:
             print("PASS: Auto-fill button passes 'this'")
        else:
             print("FAIL: Auto-fill button does not pass 'this'")

        # 4. Take a screenshot of the meshing page
        # We need to ensure the section is visible.
        # Since JS might not be running fully (modules), we can force visible.
        page.evaluate("document.getElementById('page-setup').classList.add('hidden')")
        page.evaluate("document.getElementById('page-meshing').classList.remove('hidden')")
        page.evaluate("document.getElementById('blockMeshSection').classList.remove('hidden')")

        # Focus on one of the inputs to show the ring?
        # Since we rely on Tailwind CDN, it might not render the ring in screenshot if CDN is blocked or slow
        # But let's try to focus it.
        bm_min.focus()

        page.screenshot(path="verification/ux_verification.png")

        browser.close()

if __name__ == "__main__":
    verify_ux_improvements()
