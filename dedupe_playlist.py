from spotify_common import (
    create_spotify_client,
    get_playlist_tracks,
    get_user_playlists,
)

TARGET_PLAYLIST = "May '26"


def find_duplicate_positions(tracks):
    """Return the {uri, position} entries to remove, keeping the first occurrence
    of each track URI and marking later occurrences as duplicates."""
    seen = set()
    duplicates = []
    for track in tracks:
        if track["uri"] in seen:
            duplicates.append(track)
        else:
            seen.add(track["uri"])
    return duplicates


def remove_positions(sp, playlist_id, duplicates):
    """Remove specific duplicate occurrences (by uri + position) in batches of 100."""
    # Remove highest positions first so earlier positions stay valid as we go.
    duplicates = sorted(duplicates, key=lambda d: d["position"], reverse=True)
    for i in range(0, len(duplicates), 100):
        batch = duplicates[i : i + 100]
        snapshot = sp.playlist(playlist_id)["snapshot_id"]
        sp.playlist_remove_specific_occurrences_of_items(
            playlist_id,
            [{"uri": d["uri"], "positions": [d["position"]]} for d in batch],
            snapshot_id=snapshot,
        )


def main():
    sp = create_spotify_client()
    user = sp.current_user()
    print(f"Logged in as: {user.get('display_name', user['id'])}")

    playlist_id = get_user_playlists(sp, user["id"]).get(TARGET_PLAYLIST)
    if not playlist_id:
        print(f"Playlist '{TARGET_PLAYLIST}' not found.")
        return

    tracks = get_playlist_tracks(sp, playlist_id)
    print(f"Playlist '{TARGET_PLAYLIST}' has {len(tracks)} track(s).")

    duplicates = find_duplicate_positions(tracks)
    if not duplicates:
        print("No duplicate tracks found.")
        return

    print(f"Found {len(duplicates)} duplicate track(s) — removing...")
    remove_positions(sp, playlist_id, duplicates)
    print("Done. Duplicates removed (kept the first occurrence of each track).")


if __name__ == "__main__":
    main()
