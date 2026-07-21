import calendar
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from spotify_common import (
    add_tracks,
    create_spotify_client,
    get_playlist_track_uris,
    get_user_playlists,
    iter_all_items,
)

LOCAL_TZ = ZoneInfo("America/New_York")
SONGS_PLAYLIST = "Songs"


def get_recent_liked_songs(sp, since_days=3):
    """Return liked songs added within the last `since_days` days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    songs = []
    for item in iter_all_items(sp, sp.current_user_saved_tracks(limit=50)):
        added_at = datetime.fromisoformat(item["added_at"].replace("Z", "+00:00"))
        if added_at < cutoff:
            break  # items are newest-first; stop early
        songs.append({
            "uri":      item["track"]["uri"],
            "name":     item["track"]["name"],
            "added_at": added_at,
        })
    return songs


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


def is_last_day_of_month():
    today = datetime.now(timezone.utc)
    last_day = calendar.monthrange(today.year, today.month)[1]
    return today.day == last_day


def playlist_name_for_month(dt):
    """Return a playlist name like "April '26" for the given datetime."""
    return dt.strftime("%B '%y")


def sync_liked_songs(sp, playlists):
    """Add recently liked songs to the current month's playlist, creating it if needed."""
    recently_liked = get_recent_liked_songs(sp, since_days=3)
    print(f"Found {len(recently_liked)} recently liked song(s)")

    playlist_name = playlist_name_for_month(datetime.now(LOCAL_TZ))
    playlist_id = playlists.get(playlist_name)
    if playlist_id is None:
        print(f"Creating playlist: {playlist_name}")
        playlist_id = create_playlist(sp, playlist_name)
        playlists[playlist_name] = playlist_id

    existing_uris = set(get_playlist_track_uris(sp, playlist_id))
    new_uris = [s["uri"] for s in recently_liked if s["uri"] not in existing_uris]
    if new_uris:
        add_tracks(sp, playlist_id, new_uris)
        print(f"Added {len(new_uris)} track(s) to '{playlist_name}'")
    else:
        print("No recently liked songs to sync.")


def copy_month_into_songs(sp, playlists):
    """Copy the current month's playlist into the main 'Songs' playlist."""
    month_name = playlist_name_for_month(datetime.now(LOCAL_TZ))

    if month_name not in playlists:
        print(f"Monthly playlist '{month_name}' not found; nothing to copy.")
        return
    if SONGS_PLAYLIST not in playlists:
        print(f"Couldn't find '{SONGS_PLAYLIST}' playlist; nothing to copy into.")
        return

    print(f"Last day of month — copying '{month_name}' into '{SONGS_PLAYLIST}'")
    monthly_uris = get_playlist_track_uris(sp, playlists[month_name])
    already_in_songs = set(get_playlist_track_uris(sp, playlists[SONGS_PLAYLIST]))
    new_uris = [u for u in monthly_uris if u not in already_in_songs]

    if new_uris:
        add_tracks(sp, playlists[SONGS_PLAYLIST], new_uris)
        print(f"Added {len(new_uris)} track(s) from '{month_name}' to '{SONGS_PLAYLIST}'")
    else:
        print(f"All tracks from '{month_name}' are already in '{SONGS_PLAYLIST}'")


def main():
    sp = create_spotify_client()
    user = sp.current_user()
    print(f"Logged in as: {user.get('display_name', user['id'])}")

    playlists = get_user_playlists(sp, user["id"])
    sync_liked_songs(sp, playlists)

    if is_last_day_of_month():
        copy_month_into_songs(sp, playlists)


if __name__ == "__main__":
    main()
