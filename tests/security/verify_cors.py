import requests
import sys

def verify_cors():
    url = "http://localhost:5000/api/plot_data?tutorial=cavity"
    headers = {"Origin": "http://evil.com"}

    print(f"Verifying CORS: Requesting {url} with Origin: http://evil.com")

    try:
        response = requests.get(url, headers=headers)
        acao = response.headers.get("Access-Control-Allow-Origin")
        print(f"[CORS] Status: {response.status_code}")
        print(f"[CORS] ACAO Header: {acao}")

        if acao == "*" or acao == "http://evil.com":
            print("FAILED: Vulnerable to CORS (Evil origin allowed)")
            sys.exit(1)
        else:
            print("PASSED: Secure against CORS (Evil origin not echoed)")
            sys.exit(0)

    except Exception as e:
        print(f"[CORS] Request failed: {e}")
        # If request fails connection refused, that's a different issue, but secure :)
        sys.exit(1)

if __name__ == "__main__":
    verify_cors()
