"""Monthly sync: on the last day of the month, copy that month's playlist into 'Songs'."""

import calendar
from datetime import datetime

from spotify_common import (
    LOCAL_TZ,
    add_tracks,
    create_spotify_client,
    get_playlist_track_uris,
    get_user_playlists,
    playlist_name_for_month,
)

SONGS_PLAYLIST = "Songs"


def is_last_day_of_month():
    today = datetime.now(LOCAL_TZ)
    last_day = calendar.monthrange(today.year, today.month)[1]
    return today.day == last_day


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
    if not is_last_day_of_month():
        print("Not the last day of the month — nothing to do.")
        return

    sp = create_spotify_client()
    user = sp.current_user()
    print(f"Logged in as: {user.get('display_name', user['id'])}")

    playlists = get_user_playlists(sp, user["id"])
    copy_month_into_songs(sp, playlists)


if __name__ == "__main__":
    main()
