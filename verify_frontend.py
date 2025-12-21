
from playwright.sync_api import sync_playwright, expect
import os

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # Load the local HTML file
    cwd = os.getcwd()
    file_path = f"file://{cwd}/static/html/foamflask_frontend.html"
    print(f"Loading {file_path}")
    page.goto(file_path)

    # 1. Verify 'Import Tutorial' loading state components
    import_btn = page.get_by_role("button", name="Import Tutorial")
    expect(import_btn).to_be_visible()

    # 2. Verify accessibility improvements

    # -- GEOMETRY PAGE --
    # Manually unhide the geometry page
    # Note: We must ensure parent containers are visible if any
    page.eval_on_selector("#page-geometry", "el => el.classList.remove('hidden')")

    # Check 'Available Geometries' label association
    geo_label = page.get_by_text("Available Geometries")
    expect(geo_label).to_be_visible()

    # Check if the label is associated with the select (this validates the 'for' attribute)
    geo_select = page.get_by_label("Available Geometries")
    expect(geo_select).to_be_visible()
    expect(geo_select).to_have_attribute("id", "geometrySelect")
    print("Geometry page accessibility verified.")

    # -- VISUALIZER PAGE --
    # Manually unhide the visualizer page
    page.eval_on_selector("#page-visualizer", "el => el.classList.remove('hidden')")

    # Verify meshSelect has aria-label
    mesh_select = page.locator("#meshSelect")
    expect(mesh_select).to_have_attribute("aria-label", "Select Mesh File")
    print("Visualizer page accessibility verified.")

    # -- POST PAGE --
    # Manually unhide the post page
    page.eval_on_selector("#page-post", "el => el.classList.remove('hidden')")

    # Verify VTK File Select label association
    vtk_select = page.get_by_label("Select VTK File")
    expect(vtk_select).to_be_visible()
    expect(vtk_select).to_have_attribute("id", "vtkFileSelect")

    # Verify Scalar Field label association
    # The error indicated that "Scalar Field" label matched multiple elements because
    # there are other elements with "Scalar Field" in their aria-label in the same page.
    # We should be more specific, e.g. exact=True, or assume the first one is the select
    # since we added the label 'for' attribute.
    # However, get_by_label looks for <label> text or aria-label.
    # The error showed it matched <select id="scalarField"> AND <input aria-label="Scalar Field Range Minimum">.
    # We want the one that is associated with the visible label text "Scalar Field".
    # Using exact=True should fix it if the label text is exactly "Scalar Field".
    scalar_select = page.get_by_label("Scalar Field", exact=True)
    expect(scalar_select).to_be_visible()
    expect(scalar_select).to_have_attribute("id", "scalarField")

    # Verify Color Map label association
    color_map_select = page.get_by_label("Color Map")
    expect(color_map_select).to_be_visible()
    expect(color_map_select).to_have_attribute("id", "colorMap")
    print("Post page accessibility verified.")

    print("Verification successful!")

    # Take a screenshot of the Post page which is now visible
    page.screenshot(path="verification_frontend.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
