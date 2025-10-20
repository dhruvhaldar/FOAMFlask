import os
import subprocess
from flask import current_app

def init_build_system(app):
    """Initialize the build system with the Flask app."""
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
