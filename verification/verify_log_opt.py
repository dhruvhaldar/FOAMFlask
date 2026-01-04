
import os
import sys
from playwright.sync_api import sync_playwright

# Ensure verification directory exists
os.makedirs("verification", exist_ok=True)

def verify_log_rendering():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Create a simple HTML page to test the logic in isolation
        # This avoids issues with the full app HTML trying to load missing resources
        page.set_content("""
            <html>
                <body>
                    <div id="output"></div>
                    <script>
                        window.outputBuffer = [];
                        window.cachedLogHTML = "";
                        window.outputFlushTimer = null;

                        window.flushOutputBuffer = () => {
                            if (outputBuffer.length === 0) {
                                outputFlushTimer = null;
                                return;
                            }
                            const container = document.getElementById("output");
                            if (!container) return;

                            const fragment = document.createDocumentFragment();
                            let newHtmlChunks = "";

                            // Helper for manual HTML escaping
                            const escapeHtml = (str) => {
                                return str
                                .replace(/&/g, "&amp;")
                                .replace(/</g, "&lt;")
                                .replace(/>/g, "&gt;")
                                .replace(/"/g, "&quot;")
                                .replace(/'/g, "&#039;");
                            };

                            outputBuffer.forEach(({ message, type }) => {
                                let className = "text-green-700";
                                if (type === "stderr") className = "text-red-600";
                                else if (type === "tutorial") className = "text-blue-600 font-semibold";
                                else if (type === "info") className = "text-yellow-600 italic";

                                const line = document.createElement("div");
                                line.className = className;
                                line.textContent = message;
                                fragment.appendChild(line);

                                const safeMessage = escapeHtml(message);
                                newHtmlChunks += `<div class="${className}">${safeMessage}</div>`;
                            });

                            container.appendChild(fragment);
                            cachedLogHTML += newHtmlChunks;
                            outputBuffer.length = 0;
                            outputFlushTimer = null;
                        };
                    </script>
                </body>
            </html>
        """)

        # Add data to buffer
        page.evaluate("""
            outputBuffer.push({ message: "INFO: Simulation started", type: "info" });
            outputBuffer.push({ message: "Error: Something went wrong", type: "stderr" });
            outputBuffer.push({ message: "Running tutorial <foam>", type: "tutorial" });
            flushOutputBuffer();
        """)

        # Verify DOM
        content = page.locator("#output").inner_html()
        print(f"DOM Content: {content}")

        # Verify Cache
        cache = page.evaluate("cachedLogHTML")
        print(f"Cache Content: {cache}")

        # Screenshot
        page.locator("#output").screenshot(path="verification/log_output.png")

        browser.close()

if __name__ == "__main__":
    verify_log_rendering()
