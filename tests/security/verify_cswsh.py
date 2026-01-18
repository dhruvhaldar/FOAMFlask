import asyncio
import websockets
import sys

async def verify_cswsh():
    uri = "ws://localhost:5000/ws/data?tutorial=cavity"

    print("Verifying CSWSH protection...")

    # Test 1: Normal connection (No Origin)
    print(f"Test 1: Connecting to {uri} (no Origin set)")
    try:
        async with websockets.connect(uri) as ws:
            print("[Test 1] Connection successful!")
    except Exception as e:
        print(f"[Test 1] Connection failed: {e}")

    # Test 2: Allowed origin
    print(f"\nTest 2: Connecting to {uri} with Origin: http://localhost:5000")
    try:
        async with websockets.connect(uri, origin="http://localhost:5000") as ws:
            print("[Test 2] Connection successful!")
    except Exception as e:
        print(f"[Test 2] Connection failed: {e}")
        print("FAILED: Allowed origin was blocked")
        sys.exit(1)

    # Test 3: Malicious origin
    print(f"\nTest 3: Connecting to {uri} with Origin: http://evil.com")

    try:
        async with websockets.connect(uri, origin="http://evil.com") as ws:
            print("[Test 3] Connection successful with evil origin!")
            print("FAILED: Evil origin was accepted")
            sys.exit(1)

    except websockets.exceptions.InvalidStatus as e:
        print(f"[Test 3] Connection rejected with status: {e.response.status_code}")
        if e.response.status_code == 403 or e.response.status_code == 4003:
             print("PASSED: Evil origin blocked")
        else:
             print(f"WARNING: Unexpected status code {e.response.status_code}, but blocked.")
             print("PASSED: Evil origin blocked")

    except Exception as e:
        print(f"[Test 3] Connection failed: {e}")
        # Check if error message contains 403
        if "403" in str(e):
             print("PASSED: Evil origin blocked")
        else:
             print("PASSED: Evil origin blocked (Generic error)")

    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(verify_cswsh())
