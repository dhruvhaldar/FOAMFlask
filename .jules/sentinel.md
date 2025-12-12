# Sentinel Journal

## 2024-05-22 - Debug Mode in Production
**Vulnerability:** `debug=True` was hardcoded in `app.run()`.
**Learning:** Hardcoding debug mode is a common mistake that exposes the Werkzeug debugger, allowing arbitrary code execution.
**Prevention:** Always use environment variables for configuration and default to secure settings (debug=False).
