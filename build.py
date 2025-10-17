import os
import sys
from pathlib import Path
from python_minifier import minify

def minify_file(input_path, output_path=None):
    """Minify a single file."""
    if output_path is None:
        output_path = input_path
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Only minify if the file has content
        if code.strip():
            minified = minify(
                code,
                remove_annotations=True,
                remove_pass=True,
                combine_imports=True,
                hoist_literals=True,
                remove_asserts=True,
                remove_debug=True,
                remove_explicit_returns=True,
                remove_pass_statements=True,
                remove_print_statements=True,
            )
            
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(minified)
            print(f"Minified: {input_path} -> {output_path}")
        else:
            print(f"Skipping empty file: {input_path}")
            
    except Exception as e:
        print(f"Error minifying {input_path}: {str(e)}", file=sys.stderr)

def update_html_references():
    """Update HTML to reference minified files."""
    html_path = os.path.join('static', 'foamchalak_frontend.html')
    if not os.path.exists(html_path):
        print(f"HTML file not found: {html_path}")
        return
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Update JavaScript reference
    original_js = "{{ url_for('static', filename='js/foamchalak_frontend.js') }}"
    min_js = "{{ url_for('static', filename='js/foamchalak_frontend.min.js') }}"
    
    if min_js not in html:
        html = html.replace(original_js, min_js)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Updated HTML to use minified JavaScript")

def main():
    # Create minified versions
    js_path = os.path.join('static', 'js', 'foamchalak_frontend.js')
    min_js_path = os.path.join('static', 'js', 'foamchalak_frontend.min.js')
    
    if os.path.exists(js_path):
        minify_file(js_path, min_js_path)
    
    # Update HTML to use minified files
    update_html_references()
    
    print("Build complete!")

if __name__ == "__main__":
    main()
