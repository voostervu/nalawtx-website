#!/usr/bin/env python3
"""
One-time setup for the Google Business Profile poster. Run on your own computer.

1. In Google Cloud Console (the project whose Business Profile API access was
   approved): APIs & Services > Credentials > Create credentials >
   OAuth client ID > Application type "Desktop app". Copy the client ID and secret.
2. Run:  python3 .github/scripts/gbp_auth.py CLIENT_ID CLIENT_SECRET
3. Your browser opens. Sign in with the Google account that manages the
   firm's Business Profile and click Allow.
4. The script prints the five values to save as GitHub repo secrets
   (Settings > Secrets and variables > Actions):
   GBP_CLIENT_ID, GBP_CLIENT_SECRET, GBP_REFRESH_TOKEN, GBP_ACCOUNT_ID, GBP_LOCATION_ID

Standard library only; nothing to install.
"""

import http.server
import json
import secrets
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser

SCOPE = "https://www.googleapis.com/auth/business.manage"
PORT = 8765
REDIRECT = f"http://localhost:{PORT}/"


def get_json(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    client_id, client_secret = sys.argv[1], sys.argv[2]
    state = secrets.token_urlsafe(16)
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state and "code" in q:
                result["code"] = q["code"][0]
                msg = "Done. You can close this tab and go back to the terminal."
            else:
                msg = "Sign-in failed or was cancelled. Run the script again."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(msg.encode())

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("localhost", PORT), Handler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state,
    })
    print("Opening your browser to sign in. If it does not open, visit:\n" + url)
    webbrowser.open(url)
    thread.join()
    server.server_close()
    if "code" not in result:
        sys.exit("No sign-in code received.")

    data = urllib.parse.urlencode({
        "code": result["code"], "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": REDIRECT, "grant_type": "authorization_code",
    }).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data, timeout=30) as r:
        tokens = json.load(r)
    refresh, access = tokens.get("refresh_token"), tokens["access_token"]
    if not refresh:
        sys.exit("Google did not return a refresh token. Remove the app's access at "
                 "https://myaccount.google.com/permissions and run again.")

    accounts = get_json("https://mybusinessaccountmanagement.googleapis.com/v1/accounts", access)
    print("\nBusiness Profile accounts and locations:")
    for acct in accounts.get("accounts", []):
        acct_id = acct["name"].split("/")[1]
        locs = get_json(
            f"https://mybusinessbusinessinformation.googleapis.com/v1/{acct['name']}/locations"
            "?readMask=name,title,storefrontAddress&pageSize=100", access)
        for loc in locs.get("locations", []):
            print(f"  account {acct_id}  location {loc['name'].split('/')[1]}  {loc.get('title', '')}")

    print("\nSave these as GitHub repo secrets:")
    print(f"  GBP_CLIENT_ID      {client_id}")
    print(f"  GBP_CLIENT_SECRET  {client_secret}")
    print(f"  GBP_REFRESH_TOKEN  {refresh}")
    print("  GBP_ACCOUNT_ID     (the account number above for Nguyen & Associates)")
    print("  GBP_LOCATION_ID    (the location number above for Nguyen & Associates)")


if __name__ == "__main__":
    main()
