from playwright.sync_api import sync_playwright
import time
import os

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    cwd = os.getcwd()
    page.goto(f"file://{cwd}/verification/temp_frontend.html")

    # Force the Geometry tab to be visible (ignoring JS logic)
    page.evaluate("""
        document.getElementById('page-geometry').classList.remove('hidden');
        document.getElementById('page-setup').classList.add('hidden');
        // Ensure no-case-state is hidden
        document.getElementById('no-case-state').classList.add('hidden');
    """)

    # Locate drop zone
    drop_zone = page.locator("#geo-drop-zone")

    # Take screenshot of default state
    drop_zone.screenshot(path="verification/geo_default.png")

    # Simulate Drag Over state (Show Overlay) manually
    # matches logic in static/ts/foamflask_frontend.ts
    page.evaluate("""
        const dropZone = document.getElementById('geo-drop-zone');
        const overlay = document.getElementById('geo-drop-overlay');
        dropZone.classList.add('border-cyan-500');
        overlay.classList.remove('opacity-0', 'scale-95');
        overlay.classList.add('opacity-100', 'scale-100');
    """)

    # Wait for transition
    time.sleep(0.5)

    # Take screenshot of drag state
    drop_zone.screenshot(path="verification/geo_drag_active.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
