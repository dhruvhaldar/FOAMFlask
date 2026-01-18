
from playwright.sync_api import Page, expect, sync_playwright
import time

def verify_logo(page: Page):
    # Go to the homepage
    page.goto("http://localhost:5000")

    # Wait for the logo image to be visible
    logo = page.locator("nav#navbar img[alt='FOAMFlask Logo']")
    expect(logo).to_be_visible()

    # Check if the logo src is correct (contains icons/logo.svg)
    expect(logo).to_have_attribute("src", "/static/icons/logo.svg")

    # Take a screenshot of the navbar area
    navbar = page.locator("nav#navbar")
    navbar.screenshot(path="verification/logo_verification.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_logo(page)
            print("Verification successful!")
        except Exception as e:
            print(f"Verification failed: {e}")
        finally:
            browser.close()
