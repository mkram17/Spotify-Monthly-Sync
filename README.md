# Spotify Monthly Playlist Sync

A GitHub Action that automatically adds every song you like on Spotify into a
private monthly playlist — e.g. **"Liked - April 2026"**.

Runs every 6 hours. Safe to re-run — **never adds duplicates**.

---

## Setup (~10 minutes)

### 1. Create a Spotify app

1. Go to https://developer.spotify.com/dashboard and click **Create app**.
2. Give it any name and description.
3. Set the **Redirect URI** to `http://localhost:8888/callback` and save.
4. Copy your **Client ID** and **Client Secret** from the app dashboard.

### 2. Push this repo to GitHub

Create a new GitHub repo and push all four files in this folder to it.

### 3. Get your refresh token (one-time, runs on your computer)

```bash
pip install requests
python get_refresh_token.py
```

A browser window opens asking you to log into Spotify and approve the app.
After you click **Accept**, the script prints your three secrets in the terminal.

### 4. Add secrets to GitHub

Go to your repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret name             | Value          |
|-------------------------|----------------|
| `SPOTIFY_CLIENT_ID`     | From step 1    |
| `SPOTIFY_CLIENT_SECRET` | From step 1    |
| `SPOTIFY_REFRESH_TOKEN` | From step 3    |

### 5. Enable and test

Go to the **Actions** tab, enable workflows if prompted, then click
**Run workflow** to trigger an immediate run and confirm it works.

---

## How it works

| Step    | What happens |
|---------|-------------|
| Trigger | Runs every 6 hours (or manually via Actions tab) |
| Fetch   | Gets songs you liked in the last 3 days via Spotify API |
| Group   | Groups them by month using the `added_at` timestamp |
| Create  | Creates a private playlist like "Liked - April 2026" if it does not exist yet |
| Add     | Adds only songs not already in the playlist (no duplicates ever) |

---

## Files

| File | Purpose |
|------|---------|
| `sync_spotify.py` | Main sync script — runs in the GitHub Action |
| `get_refresh_token.py` | One-time local helper to authorize and get your refresh token |
| `.github/workflows/spotify-sync.yml` | GitHub Actions workflow definition |
| `README.md` | This file |
