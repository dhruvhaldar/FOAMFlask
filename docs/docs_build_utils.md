# build_utils API documentation

Module: `build_utils`

This document contains the API documentation for the build utilities extracted from the generated HTML docs.

---

## Functions

### init_build_system(app)

Initialize the build system with the Flask app.

```python
def init_build_system(app):
    """Initialize the build system with the Flask app.
    
    Args:
        app (Flask): The Flask app.
    """
    @app.before_first_request
    def run_build():
        if app.config.get('ENV') == 'development':
            # In development, we'll run the build process
            try:
                # Check if python-minifier is installed
                import python_minifier  # noqa
                
                # Run the build script
                result = subprocess.run(
                    [sys.executable, 'build.py'],
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    current_app.logger.info("Build completed successfully")
                    if result.stdout:
                        current_app.logger.debug(f"Build output: {result.stdout}")
                else:
                    current_app.logger.error(f"Build failed: {result.stderr}")
                    
            except ImportError:
                current_app.logger.warning(
                    "python-minifier not installed. "
                    "Run 'pip install python-minifier' to enable minification."
                )
            except Exception as e:
                current_app.logger.error(f"Error during build: {str(e)}")
        else:
            # In production, just check if minified files exist
            min_js = os.path.join('static', 'js', 'foamflask_frontend.min.js')
            if not os.path.exists(min_js):
                current_app.logger.warning(
                    "Minified JavaScript not found. "
                    "Run 'python build.py' to generate minified files."
                )
```

Args:
- app (Flask): The Flask app.

---

Original HTML source: https://github.com/dhruvhaldar/FOAMFlask/blob/17a1c303767759ae3f1c56910b2a00afa66f1890/docs/build_utils.html