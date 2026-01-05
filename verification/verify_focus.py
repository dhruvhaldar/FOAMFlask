
from playwright.sync_api import sync_playwright

def verify_focus_styles():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load the file directly since it's static HTML
        page.goto('file:///app/static/html/foamflask_frontend.html')

        # Define elements to check
        elements_to_check = [
            {'name': 'Setup Button', 'selector': '#nav-setup'},
            {'name': 'Geometry Button', 'selector': '#nav-geometry'},
            {'name': 'Case Select', 'selector': '#caseSelect'},
            {'name': 'Tutorial Select', 'selector': '#tutorialSelect'}
        ]

        # Mocking window properties if needed, but for CSS check it should be fine

        for el in elements_to_check:
            print(f'Checking {el["name"]}...')
            element = page.locator(el['selector'])

            # Focus the element
            element.focus()

            # Take a screenshot of the focused element
            page.screenshot(path=f'/app/verification/focus_{el["selector"].replace("#", "")}.png')

            # Check for focus ring classes
            # Note: We can't easily check computed styles for Tailwind classes in a robust way
            # without knowing the exact computed border/ring, but we can check if the class is present.
            # However, verifying visual change via screenshot is better.

            # For automation, we can check if the element has the expected classes in the DOM
            class_attr = element.get_attribute('class')
            expected_classes = ['focus:ring-2', 'focus:ring-blue-500']
            for cls in expected_classes:
                if cls not in class_attr:
                    print(f'❌ Missing class {cls} on {el["name"]}')
                else:
                    print(f'✅ Found class {cls} on {el["name"]}')

        browser.close()

if __name__ == '__main__':
    verify_focus_styles()
