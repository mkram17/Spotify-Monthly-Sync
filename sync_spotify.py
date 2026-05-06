import calendar
import os
import requests
from datetime import datetime, timezone, timedelta
import base64

CLIENT_ID     = os.environ["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["SPOTIFY_REFRESH_TOKEN"]


def get_access_token():
    creds = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    r = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN},
    )
    r.raise_for_status()
    return r.json()["access_token"]


def get_current_user(token):
    r = requests.get("https://api.spotify.com/v1/me",
                     headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json()


def get_recent_liked_songs(token, since_days=3):
    """Return liked songs added within the last `since_days` days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    songs = []
    url = "https://api.spotify.com/v1/me/tracks?limit=50"
    while url:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        data = r.json()
        for item in data["items"]:
            added_at = datetime.fromisoformat(item["added_at"].replace("Z", "+00:00"))
            if added_at < cutoff:
                return songs  # items are newest-first; stop early
            songs.append({
                "uri":      item["track"]["uri"],
                "name":     item["track"]["name"],
                "added_at": added_at,
            })
        url = data.get("next")
    return songs


def get_user_playlists(token, user_id):
    """Return {playlist_name: playlist_id} for all playlists owned by user."""
    playlists = {}
    url = "https://api.spotify.com/v1/me/playlists?limit=50"
    while url:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        data = r.json()
        for pl in data["items"]:
            if pl["owner"]["id"] == user_id:
                playlists[pl["name"]] = pl["id"]
        url = data.get("next")
    return playlists


def create_playlist(token, user_id, name):
    r = requests.post(
        f"https://api.spotify.com/v1/users/{user_id}/playlists",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "name":        name,
            "public":      False,
            "description": "Auto-generated monthly liked-songs playlist",
        },
    )
    r.raise_for_status()
    return r.json()["id"]


def get_playlist_track_uris(token, playlist_id):
    """Return a set of all track URIs already in the playlist."""
    uris = set()
    url = (
        f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        "?fields=items(track(uri)),next&limit=100"
    )
    while url:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        data = r.json()
        for item in data["items"]:
            if item.get("track"):
                uris.add(item["track"]["uri"])
        url = data.get("next")
    return uris


def add_tracks(token, playlist_id, uris):
    for i in range(0, len(uris), 100):
        r = requests.post(
            f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"uris": uris[i : i + 100]},
        )
        r.raise_for_status()


def is_last_day_of_month():
    today = datetime.now(timezone.utc)
    last_day = calendar.monthrange(today.year, today.month)[1]
    return today.day == last_day


def main():
    token   = get_access_token()
    user    = get_current_user(token)
    user_id = user["id"]
    print(f"Logged in as: {user.get('display_name', user_id)}")

    songs = get_recent_liked_songs(token, since_days=3)
    print(f"Found {len(songs)} recently liked song(s) to sync")

    existing = get_user_playlists(token, user_id)

    if songs:
        by_month = {}
        for song in songs:
            key = song["added_at"].strftime("%B '%y")  # e.g. "April '26"
            by_month.setdefault(key, []).append(song["uri"])

        for month_name, uris in by_month.items():
            playlist_name = month_name

            if playlist_name not in existing:
                print(f"Creating playlist: {playlist_name}")
                pid = create_playlist(token, user_id, playlist_name)
                existing[playlist_name] = pid
            else:
                pid = existing[playlist_name]

            already_there = get_playlist_track_uris(token, pid)
            new_uris = [u for u in uris if u not in already_there]

            if new_uris:
                add_tracks(token, pid, new_uris)
                print(f"Added {len(new_uris)} track(s) to '{playlist_name}'")
            else:
                print(f"No new tracks to add to '{playlist_name}'")
    else:
        print("No recently liked songs to sync.")

    if is_last_day_of_month():
        today = datetime.now(timezone.utc)
        month_name = today.strftime("%B '%y")
        songs_playlist = "Songs"

        print(f"Last day of month — copying '{month_name}' into '{songs_playlist}'")

        if month_name not in existing:
            print(f"Monthly playlist '{month_name}' not found; nothing to copy.")
            return

        if songs_playlist not in existing:
            print(f"Playlist '{songs_playlist}' not found; nothing to copy into.")
            return

        monthly_uris = list(get_playlist_track_uris(token, existing[month_name]))
        already_in_songs = get_playlist_track_uris(token, existing[songs_playlist])
        new_uris = [u for u in monthly_uris if u not in already_in_songs]

        if new_uris:
            add_tracks(token, existing[songs_playlist], new_uris)
            print(f"Added {len(new_uris)} track(s) from '{month_name}' to '{songs_playlist}'")
        else:
            print(f"All tracks from '{month_name}' are already in '{songs_playlist}'")


if __name__ == "__main__":
    main()
