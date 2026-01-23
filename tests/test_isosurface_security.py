
import pytest
from backend.post.isosurface import IsosurfaceVisualizer

def test_generate_error_html_xss_protection():
    """
    Test that _generate_error_html in IsosurfaceVisualizer protects against XSS
    by escaping inputs.
    """
    visualizer = IsosurfaceVisualizer()

    malicious_scalar_field = "<script>alert('XSS')</script>"
    malicious_error_message = "An error <img src=x onerror=alert(1)> occurred"

    html = visualizer._generate_error_html(malicious_error_message, malicious_scalar_field)

    # Check that the malicious script tags are escaped (secure behavior)
    assert "<script>" not in html, "Script tag was not escaped"
    assert "&lt;script&gt;" in html, "Escaped script tag not found"

    assert "<img" not in html, "Image tag was not escaped"
    assert "&lt;img" in html, "Escaped image tag not found"

if __name__ == "__main__":
    test_generate_error_html_xss_protection()
    print("Test passed: XSS protection confirmed.")
