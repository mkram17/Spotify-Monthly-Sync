import os

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

CLIENT_ID     = os.environ["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["SPOTIFY_REFRESH_TOKEN"]

# A refresh token is permanently bound to the scopes granted when it was
# authorized. Both scripts share one token, so we request the union here.
SCOPES = (
    "user-library-read "
    "playlist-read-private "
    "playlist-modify-private "
    "playlist-modify-public"
)


def create_spotify_client(scope=SCOPES):
    """Create a spotipy client authorized as the user via the refresh token."""
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri="http://127.0.0.1:8888/callback",
        scope=scope,
        open_browser=False,
    )
    # Use the stored refresh token to obtain a valid access token.
    token_info = auth_manager.refresh_access_token(REFRESH_TOKEN)

    # A refresh token carries only the scopes granted when it was authorized,
    # so verify it actually has what the caller needs before we rely on it.
    granted = set(token_info.get("scope", "").split())
    missing = set(scope.split()) - granted
    if missing:
        raise SystemExit(
            f"Refresh token is missing scope(s): {', '.join(sorted(missing))}. "
            f"Granted: {', '.join(sorted(granted)) or '(none reported)'}. "
            "Re-run get_refresh_token.py and update the SPOTIFY_REFRESH_TOKEN secret."
        )

    return spotipy.Spotify(auth=token_info["access_token"])


def iter_all_items(sp, results):
    """Yield every item across all pages of a spotipy paging result."""
    while results:
        yield from results["items"]
        results = sp.next(results) if results["next"] else None


def get_user_playlists(sp, user_id):
    """Return {playlist_name: playlist_id} for all playlists owned by the user."""
    return {
        pl["name"]: pl["id"]
        for pl in iter_all_items(sp, sp.current_user_playlists(limit=50))
        if pl["owner"]["id"] == user_id
    }


def get_playlist_tracks(sp, playlist_id):
    """Return an ordered list of {uri, position} for each real track.

    `position` counts every slot (including empty/unavailable ones) so it stays
    valid for Spotify's position-based remove endpoint.
    """
    tracks = []
    for position, item in enumerate(iter_all_items(sp, sp.playlist_items(playlist_id))):
        track = item.get("item")
        if track and track.get("uri"):
            tracks.append({"uri": track["uri"], "position": position})
    return tracks


def get_playlist_track_uris(sp, playlist_id):
    """Return the ordered list of track URIs in the playlist."""
    return [t["uri"] for t in get_playlist_tracks(sp, playlist_id)]


def add_tracks(sp, playlist_id, uris):
    """Add track URIs to a playlist, batching within the API's 100-item limit."""
    for i in range(0, len(uris), 100):
        sp.playlist_add_items(playlist_id, uris[i : i + 100])
