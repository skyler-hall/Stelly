"""
Music tool. Lets Stelly search Spotify and start playback on whatever
device is currently active, phone, speaker, desktop app, wherever Skyler
has Spotify open.

Uses spotipy, which handles the OAuth token refresh once the first login
has happened. First run will open a browser link for Skyler to approve
access, after that the refresh token is cached locally in .spotify_cache
(gitignored) and no more logins are needed.
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from config import settings

SCOPE = "user-modify-playback-state user-read-playback-state"

_client = None


def _get_client():
    """Lazy singleton so authentication happens once per process, not
    once per tool call."""
    global _client
    if _client is None:
        _client = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=settings.require(settings.SPOTIFY_CLIENT_ID, "SPOTIFY_CLIENT_ID"),
            client_secret=settings.require(settings.SPOTIFY_CLIENT_SECRET, "SPOTIFY_CLIENT_SECRET"),
            redirect_uri=settings.require(settings.SPOTIFY_REDIRECT_URI, "SPOTIFY_REDIRECT_URI"),
            scope=SCOPE,
            cache_path=".spotify_cache",
        ))
    return _client


def play_music(query: str) -> str:
    """Search Spotify for query and start playing the first matching
    track on the active device. Returns a short status line Stelly can
    speak back, this is what the tool result sends to Claude."""
    client = _get_client()

    devices = client.devices().get("devices", [])
    if not devices:
        return "Stelly could not find any Spotify device. Open Spotify somewhere first."

    active = next((d for d in devices if d["is_active"]), devices[0])

    results = client.search(q=query, type="track", limit=1)
    tracks = results.get("tracks", {}).get("items", [])
    if not tracks:
        return f"Stelly could not find anything called {query} on Spotify."

    track = tracks[0]
    client.start_playback(device_id=active["id"], uris=[track["uri"]])

    artist = track["artists"][0]["name"] if track["artists"] else "someone"
    return f"Now playing {track['name']} by {artist} on {active['name']}."


PLAY_MUSIC_TOOL = {
    "name": "play_music",
    "description": (
        "Search Spotify and start playing a song, artist, or track on Skyler's "
        "active Spotify device. Use this when Skyler asks to hear, play, or put "
        "on a specific song or artist."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for and play, a song title or artist name.",
            },
        },
        "required": ["query"],
    },
}
