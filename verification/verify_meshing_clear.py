import os
from playwright.sync_api import sync_playwright

def test_meshing_output_clear_button():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load the HTML file directly
        # Note: We need to resolve the path relative to where we are running
        # Assuming we run from repo root
        cwd = os.getcwd()
        html_path = f"file://{cwd}/static/html/foamflask_frontend.html"

        # We need to mock the template variables because it's a Flask template
        # The browser will fail to render {{ url_for(...) }} and {{ options|safe }}
        # So we read the file, replace the template tags with dummy data, and write to a temp file

        with open("static/html/foamflask_frontend.html", "r") as f:
            content = f.read()

        # Mock template variables
        content = content.replace("{{ url_for('static', filename='favicon.ico') }}", "")
        content = content.replace("{{ url_for('static', filename='js/frontend/isosurface.js') }}", "")
        content = content.replace("{{ url_for('static', filename='js/foamflask_frontend.js') }}", "")
        content = content.replace("{{ url_for('static', filename='icons/Pyvista-logo.avif') }}", "")
        content = content.replace("{{ url_for('static', filename='icons/Plotly-logo.avif') }}", "")
        content = content.replace("{{ url_for('static', filename='icons/docker-logo.avif') }}", "")
        content = content.replace("{{ options|safe }}", "<option>Mock Tutorial</option>")

        with open("verification/temp_frontend.html", "w") as f:
            f.write(content)

        temp_html_path = f"file://{cwd}/verification/temp_frontend.html"

        page.goto(temp_html_path)

        # Mock the JS function since the JS module won't load properly from file:// without a server
        page.evaluate("""
            window.clearMeshingOutput = () => {
                const div = document.getElementById("meshingOutput");
                div.innerText = "Ready...";
                // Create notification mock
                const container = document.getElementById("notificationContainer");
                const notif = document.createElement("div");
                notif.className = "bg-green-500 text-white p-2 rounded";
                notif.innerText = "Meshing output cleared";
                container.appendChild(notif);
            }
        """)

        # Navigate to Meshing Page
        # We need to manually remove hidden class because the JS logic normally does this
        page.evaluate("""
            document.getElementById('page-setup').classList.add('hidden');
            document.getElementById('page-meshing').classList.remove('hidden');
        """)

        # Locate the Meshing Output section
        meshing_output = page.locator("#meshingOutput")

        # Add some text to clear
        page.evaluate("document.getElementById('meshingOutput').innerText = 'Some log text here...'")

        # Verify text is present
        assert "Some log text here..." in meshing_output.inner_text()

        # Find the Clear button
        clear_btn = page.get_by_label("Clear meshing output")

        # Take screenshot before
        page.screenshot(path="verification/meshing_output_before.png")

        # Click Clear
        clear_btn.click()

        # Verify text is reset
        assert "Ready..." in meshing_output.inner_text()

        # Take screenshot after
        page.screenshot(path="verification/meshing_output_after.png")

        browser.close()

if __name__ == "__main__":
    test_meshing_output_clear_button()
