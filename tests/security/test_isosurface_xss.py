
import pytest
from backend.post.isosurface import IsosurfaceVisualizer
from markupsafe import escape

def test_generate_error_html_xss():
    visualizer = IsosurfaceVisualizer()

    # Payload
    xss_payload = "<script>alert('XSS')</script>"

    # Call the function
    html = visualizer._generate_error_html("Some error", scalar_field=xss_payload)

    # Check if payload is NOT reflected (should be escaped)
    assert xss_payload not in html
    assert "&lt;script&gt;alert(&#39;XSS&#39;)&lt;/script&gt;" in html or escape(xss_payload) in html

def test_generate_error_html_message_xss():
    visualizer = IsosurfaceVisualizer()

    # Payload in error message
    xss_payload = "<img src=x onerror=alert(1)>"

    html = visualizer._generate_error_html(xss_payload, scalar_field="U")

    # Check if payload is NOT reflected (should be escaped)
    assert xss_payload not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html or escape(xss_payload) in html
