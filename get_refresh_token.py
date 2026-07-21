"""
Run this ONCE locally to get your Spotify refresh token.
It opens a browser for login, then prints the three secrets
you need to add to your GitHub repository.

  pip install requests
  python get_refresh_token.py
"""

import base64
import webbrowser
import requests
from urllib.parse import urlencode, urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler

CLIENT_ID     = input("Paste your Spotify Client ID:     ").strip()
CLIENT_SECRET = input("Paste your Spotify Client Secret: ").strip()

REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "user-library-read playlist-modify-private playlist-modify-public playlist-read-private"

auth_url = "https://accounts.spotify.com/authorize?" + urlencode({
    "client_id":     CLIENT_ID,
    "response_type": "code",
    "redirect_uri":  REDIRECT_URI,
    "scope":         SCOPES,
})

auth_code = None


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h1>All done! You can close this tab.</h1>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1>Error: no code received.</h1>")

    def log_message(self, *_):
        pass


print("\nOpening browser for Spotify login...")
print(f"If the browser doesn't open automatically, click this link:\n{auth_url}\n")
webbrowser.open(auth_url)
HTTPServer(("localhost", 8888), _Handler).handle_request()

if not auth_code:
    raise SystemExit("Failed to get the authorization code.")

creds = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
r = requests.post(
    "https://accounts.spotify.com/api/token",
    headers={
        "Authorization": f"Basic {creds}",
        "Content-Type":  "application/x-www-form-urlencoded",
    },
    data={
        "grant_type":   "authorization_code",
        "code":         auth_code,
        "redirect_uri": REDIRECT_URI,
    },
)
r.raise_for_status()
refresh_token = r.json()["refresh_token"]

print("\n" + "="*50)
print("SUCCESS! Add these 3 secrets to your GitHub repo:")
print("Settings > Secrets and variables > Actions > New repository secret")
print("="*50 + "\n")
print(f"  SPOTIFY_CLIENT_ID     =  {CLIENT_ID}")
print(f"  SPOTIFY_CLIENT_SECRET =  {CLIENT_SECRET}")
print(f"  SPOTIFY_REFRESH_TOKEN =  {refresh_token}")
