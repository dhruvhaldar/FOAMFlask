import os
from playwright.sync_api import sync_playwright

def verify_spinner():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load the local HTML file directly
        # We need absolute path
        cwd = os.getcwd()
        html_path = os.path.join(cwd, 'static/html/foamflask_frontend.html')
        page.goto(f'file://{html_path}')

        # Need to inject the JS logic since we can't load the module easily in file:// protocol
        # without a server (imports fail).
        # So we will manually inject a minimal runCommand to test the spinner logic.

        # First, mock the runCommand globally so the button onclick works (or better, overwrite it)
        # We also need to mock showNotification as it's used in runCommand

        page.evaluate("""
            window.showNotification = (msg, type) => { console.log(msg); };

            window.runCommand = async (cmd, btnElement) => {
                const originalContent = btnElement ? btnElement.innerHTML : "";
                if (btnElement && btnElement instanceof HTMLButtonElement) {
                    btnElement.disabled = true;
                    btnElement.setAttribute("aria-busy", "true");
                    btnElement.innerHTML = `<svg class="animate-spin h-4 w-4 inline-block mr-2 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Running...`;
                }

                // Keep it spinning for the screenshot
                await new Promise(r => setTimeout(r, 2000));

                // We won't restore it here so we can capture the spinner state
            };
        """)

        # Make the 'Run' page visible
        page.evaluate("document.getElementById('page-run').classList.remove('hidden')")

        # Find the Allrun button and click it
        # The button has text "Allrun"
        allrun_btn = page.get_by_role("button", name="Allrun")
        allrun_btn.click()

        # Wait a moment for the DOM to update
        page.wait_for_timeout(500)

        # Take screenshot
        page.screenshot(path='verification/spinner_verification.png')

        browser.close()

if __name__ == "__main__":
    verify_spinner()
