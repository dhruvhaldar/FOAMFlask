from playwright.sync_api import sync_playwright

def verify_focus_states():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load the HTML file directly
        import os
        cwd = os.getcwd()
        page.goto(f"file://{cwd}/static/html/foamflask_frontend.html")

        # Inject mock functions to avoid errors
        page.evaluate("""
            window.loadGeometryView = () => {};
            window.deleteGeometry = () => {};
            window.generateBlockMeshDict = () => {};
            window.runMeshingCommand = () => {};
            window.checkStartupStatus = () => {};
            window.runCommand = () => {};
        """)

        # 1. Verify Geometry Tab Button Focus
        # Navigate to Geometry Tab
        page.evaluate("document.getElementById('page-geometry').classList.remove('hidden')")

        # Focus on Upload Button
        upload_btn = page.locator("#uploadGeometryBtn")
        upload_btn.focus()
        page.screenshot(path="verification/geometry_upload_focus.png")
        print("Captured geometry_upload_focus.png")

        # Focus on View Button
        view_btn = page.locator("#viewGeometryBtn")
        view_btn.focus()
        page.screenshot(path="verification/geometry_view_focus.png")
        print("Captured geometry_view_focus.png")

        # Focus on Delete Button
        delete_btn = page.locator("#deleteGeometryBtn")
        delete_btn.focus()
        page.screenshot(path="verification/geometry_delete_focus.png")
        print("Captured geometry_delete_focus.png")

        # 2. Verify Meshing Tab Button Focus
        # Hide Geometry, Show Meshing
        page.evaluate("document.getElementById('page-geometry').classList.add('hidden')")
        page.evaluate("document.getElementById('page-meshing').classList.remove('hidden')")

        # Focus on Gen BlockMesh Button
        gen_bm_btn = page.locator("#genBlockMeshBtn")
        gen_bm_btn.focus()
        page.screenshot(path="verification/meshing_gen_bm_focus.png")
        print("Captured meshing_gen_bm_focus.png")

        # Focus on Run BlockMesh Button
        run_bm_btn = page.locator("#runBlockMeshBtn")
        run_bm_btn.focus()
        page.screenshot(path="verification/meshing_run_bm_focus.png")
        print("Captured meshing_run_bm_focus.png")

        # 3. Verify Run Tab Button Focus
        # Hide Meshing, Show Run
        page.evaluate("document.getElementById('page-meshing').classList.add('hidden')")
        page.evaluate("document.getElementById('page-run').classList.remove('hidden')")

        # Focus on Allrun Button
        run_allrun_btn = page.locator("#runAllrunBtn")
        run_allrun_btn.focus()
        page.screenshot(path="verification/run_allrun_focus.png")
        print("Captured run_allrun_focus.png")

        # Focus on Allclean Button
        run_allclean_btn = page.locator("#runAllcleanBtn")
        run_allclean_btn.focus()
        page.screenshot(path="verification/run_allclean_focus.png")
        print("Captured run_allclean_focus.png")

        browser.close()

if __name__ == "__main__":
    verify_focus_states()
