#!/bin/bash
set -e

echo "Running Backend Tests (Python)..."
python -m pytest tests/test_app.py

echo "Running Frontend E2E Tests (Playwright)..."
# Start the mock server in background? No, webServer in config handles it.

# We also need to compile TS first as E2E tests depend on built JS
echo "Building Frontend..."
pnpm build

echo "Executing Playwright..."
pnpm playwright test

echo "All tests passed!"
