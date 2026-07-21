import calendar
import os

import spotipy
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

CLIENT_ID     = os.environ["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["SPOTIFY_REFRESH_TOKEN"]

SCOPES = "user-library-read playlist-modify-private playlist-modify-public playlist-read-private"


def create_spotify_client():
    """Create a spotipy client authorized as the user via the refresh token."""
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri="http://127.0.0.1:8888/callback",
        scope=SCOPES,
        open_browser=False,
    )
    # Use the stored refresh token to obtain a valid access token
    token_info = auth_manager.refresh_access_token(REFRESH_TOKEN)

    # A refresh token is permanently bound to the scopes granted when it was
    # authorized, so verify it actually carries what this script needs.
    granted = set(token_info.get("scope", "").split())
    missing = set(SCOPES.split()) - granted
    if missing:
        raise SystemExit(
            f"Refresh token is missing scope(s): {', '.join(sorted(missing))}. "
            f"Granted: {', '.join(sorted(granted)) or '(none reported)'}. "
            "Re-run get_refresh_token.py and update the SPOTIFY_REFRESH_TOKEN secret."
        )

    return spotipy.Spotify(auth=token_info["access_token"])


def get_recent_liked_songs(sp, since_days=3):
    """Return liked songs added within the last `since_days` days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    songs = []
    results = sp.current_user_saved_tracks(limit=50)
    while results:
        for item in results["items"]:
            added_at = datetime.fromisoformat(item["added_at"].replace("Z", "+00:00"))
            if added_at < cutoff:
                return songs  # items are newest-first; stop early
            songs.append({
                "uri":      item["track"]["uri"],
                "name":     item["track"]["name"],
                "added_at": added_at,
            })
        results = sp.next(results) if results["next"] else None
    return songs


def get_user_playlists(sp, user_id):
    """Return {playlist_name: playlist_id} for all playlists owned by user."""
    playlists = {}
    results = sp.current_user_playlists(limit=50)
    while results:
        for pl in results["items"]:
            if pl["owner"]["id"] == user_id:
                playlists[pl["name"]] = pl["id"]
        results = sp.next(results) if results["next"] else None
    return playlists


def create_playlist(sp, name):
    # Spotify now returns 403 for the user-scoped create endpoint that
    # spotipy's user_playlist_create() calls, so post to me/playlists instead.
    playlist = sp._post(
        "me/playlists",
        payload={
            "name": name,
            "public": False,
            "description": "Auto-generated monthly liked-songs playlist",
        },
    )
    return playlist["id"]


def get_playlist_track_uris(sp, playlist_id):
    """Return a set of track URIs in the given playlist."""
    uris = set()
    results = sp.playlist_items(playlist_id)
    while results:
        for item in results["items"]:
            if item.get("track"):
                uris.add(item["track"]["uri"])
        results = sp.next(results) if results["next"] else None
    return uris


def add_tracks(sp, playlist_id, uris):
    for i in range(0, len(uris), 100):
        sp.playlist_add_items(playlist_id, uris[i : i + 100])


def is_last_day_of_month():
    today = datetime.now(timezone.utc)
    last_day = calendar.monthrange(today.year, today.month)[1]
    return today.day == last_day


def main():
    sp = create_spotify_client()
    user = sp.current_user()
    user_id = user["id"]
    print(f"Logged in as: {user.get('display_name', user_id)}")

    songs = get_recent_liked_songs(sp, since_days=3)
    print(f"Found {len(songs)} recently liked song(s) to sync")

    existing = get_user_playlists(sp, user_id)

    if songs:
        by_month = {}
        for song in songs:
            key = song["added_at"].strftime("%B '%y")  # e.g. "April '26"
            by_month.setdefault(key, []).append(song["uri"])

        for month_name, uris in by_month.items():
            playlist_name = month_name

            if playlist_name not in existing:
                print(f"Creating playlist: {playlist_name}")
                playlist_id = create_playlist(sp, playlist_name)
                existing[playlist_name] = playlist_id
            else:
                playlist_id = existing[playlist_name]

            already_there = get_playlist_track_uris(sp, playlist_id)
            new_uris = [u for u in uris if u not in already_there]

            if new_uris:
                add_tracks(sp, playlist_id, new_uris)
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

        monthly_uris = list(get_playlist_track_uris(sp, existing[month_name]))
        already_in_songs = get_playlist_track_uris(sp, existing[songs_playlist])
        new_uris = [u for u in monthly_uris if u not in already_in_songs]

        if new_uris:
            add_tracks(sp, existing[songs_playlist], new_uris)
            print(f"Added {len(new_uris)} track(s) from '{month_name}' to '{songs_playlist}'")
        else:
            print(f"All tracks from '{month_name}' are already in '{songs_playlist}'")


if __name__ == "__main__":
    main()
