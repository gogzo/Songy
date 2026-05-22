import os
import json
import requests
import uuid
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
import spotipy
from strands import Agent
from strands.models.openai import OpenAIModel

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

model = OpenAIModel(
    client_args={
        "api_key": OPENROUTER_KEY,
        "base_url": "https://openrouter.ai/api/v1"
    },
    model_id="openai/gpt-oss-120b:free",
)
agent = Agent(model=model)

app = FastAPI()

# In-memory session store
sessions = {}

def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope="user-read-currently-playing"
    )

def get_lyrics(title, artist):
    try:
        response = requests.get(
            "https://lrclib.net/api/get",
            params={"track_name": title, "artist_name": artist}
        )
        if response.status_code == 200:
            data = response.json()
            lyrics = data.get("plainLyrics") or data.get("syncedLyrics")
            if lyrics:
                return lyrics
        response = requests.get(
            "https://lrclib.net/api/search",
            params={"track_name": title, "artist_name": artist}
        )
        results = response.json()
        if results:
            lyrics = results[0].get("plainLyrics") or results[0].get("syncedLyrics")
            if lyrics:
                return lyrics
    except:
        pass
    return None

def analyze_lyrics(lyrics, title, artist):
    prompt = f"""Analyze these lyrics from "{title}" by {artist}:

{lyrics[:3000]}

Return a JSON object with EXACTLY these fields and nothing else, no markdown:
{{
  "overall_meaning": "what the song is really about in 2-3 sentences",
  "themes": ["theme1", "theme2", "theme3"],
  "emotional_tone": "the overall emotional vibe",
  "hidden_meaning": "a deeper or non-obvious interpretation",
  "most_powerful_line": "the most impactful line and why",
  "one_word_summary": "one word"
}}"""
    response = agent(prompt)
    text = str(response)
    clean = text[text.find("{"):text.rfind("}")+1]
    return json.loads(clean)

@app.get("/login")
def login(response: Response):
    session_id = str(uuid.uuid4())
    oauth = get_spotify_oauth()
    auth_url = oauth.get_authorize_url(state=session_id)
    resp = RedirectResponse(auth_url)
    resp.set_cookie("session_id", session_id, max_age=3600)
    return resp

@app.get("/callback")
def callback(request: Request, code: str = None, state: str = None):
    if not code:
        return RedirectResponse("/")
    oauth = get_spotify_oauth()
    token_info = oauth.get_access_token(code)
    session_id = state or request.cookies.get("session_id")
    sessions[session_id] = token_info
    resp = RedirectResponse("/")
    resp.set_cookie("session_id", session_id, max_age=3600)
    return resp

@app.get("/now-playing")
def now_playing(request: Request):
    session_id = request.cookies.get("session_id")
    token_info = sessions.get(session_id)

    if not token_info:
        return {"error": "not_logged_in"}

    try:
        oauth = get_spotify_oauth()
        if oauth.is_token_expired(token_info):
            token_info = oauth.refresh_access_token(token_info["refresh_token"])
            sessions[session_id] = token_info

        sp = spotipy.Spotify(auth=token_info["access_token"])
        current = sp.current_user_playing_track()

        if not current or not current["is_playing"]:
            return {"error": "No song playing"}

        track = current["item"]
        song = {
            "title": track["name"],
            "artist": track["artists"][0]["name"],
            "album_art": track["album"]["images"][0]["url"]
        }
    except:
        return {"error": "not_logged_in"}

    lyrics = get_lyrics(song["title"], song["artist"])
    if not lyrics:
        return {"error": "Lyrics not found"}

    analysis = analyze_lyrics(lyrics, song["title"], song["artist"])
    return {**song, **analysis}

@app.get("/", response_class=HTMLResponse)
def frontend():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Song Meaning Analyzer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            min-height: 100vh;
            background: linear-gradient(135deg, #1a0533 0%, #0d1a3a 50%, #0a2a1a 100%);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem 1rem;
        }
        h1 {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 3px;
            color: rgba(255,255,255,0.4);
            margin-bottom: 1.5rem;
            font-weight: 400;
        }
        .glass-card {
            background: rgba(255,255,255,0.07);
            border: 0.5px solid rgba(255,255,255,0.15);
            border-radius: 24px;
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            padding: 1.75rem;
            width: 100%;
            max-width: 480px;
        }
        .song-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        .album-art {
            width: 72px;
            height: 72px;
            border-radius: 12px;
            object-fit: cover;
            flex-shrink: 0;
        }
        .song-title { font-size: 1.2rem; font-weight: 500; color: #fff; margin-bottom: 4px; }
        .song-artist { font-size: 0.88rem; color: rgba(255,255,255,0.5); }
        .one-word {
            font-size: 2.8rem;
            font-weight: 500;
            text-align: center;
            background: linear-gradient(90deg, #AFA9EC, #5DCAA5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            padding: 0.5rem 0 1.25rem;
        }
        .divider {
            border: none;
            border-top: 0.5px solid rgba(255,255,255,0.08);
            margin: 0 0 1.25rem;
        }
        .section { margin-bottom: 1.25rem; }
        .label {
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: rgba(255,255,255,0.35);
            margin-bottom: 0.4rem;
        }
        .value { font-size: 0.92rem; color: rgba(255,255,255,0.8); line-height: 1.65; }
        .themes { display: flex; flex-wrap: wrap; gap: 0.5rem; }
        .theme-tag {
            background: rgba(127,119,221,0.2);
            color: #AFA9EC;
            border: 0.5px solid rgba(127,119,221,0.35);
            padding: 0.25rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
        }
        .btn {
            width: 100%;
            max-width: 480px;
            margin-top: 1rem;
            padding: 0.9rem;
            border-radius: 50px;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
            border: none;
        }
        .analyze-btn {
            background: rgba(127,119,221,0.2);
            border: 0.5px solid rgba(127,119,221,0.4);
            color: #CECBF6;
        }
        .analyze-btn:hover { background: rgba(127,119,221,0.35); }
        .analyze-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .login-btn {
            background: #1db954;
            color: #000;
            font-weight: 600;
        }
        .login-btn:hover { background: #1ed760; }
        #status {
            color: rgba(255,255,255,0.4);
            font-size: 0.9rem;
            text-align: center;
            margin-bottom: 1rem;
            min-height: 1.4rem;
        }
        @media (max-width: 520px) {
            .glass-card { padding: 1.25rem; border-radius: 20px; }
            .one-word { font-size: 2.2rem; }
        }
    </style>
</head>
<body>
    <h1>&#9835; Song Meaning Analyzer</h1>
    <div id="status">Checking your session...</div>
    <div id="card"></div>
    <div id="actions"></div>

    <script>
        async function init() {
            const res = await fetch('/now-playing');
            const data = await res.json();

            if (data.error === 'not_logged_in') {
                document.getElementById('status').textContent = 'Connect your Spotify to get started';
                document.getElementById('actions').innerHTML = `
                    <button class="btn login-btn" onclick="window.location.href='/login'">Login with Spotify</button>`;
                return;
            }

            showAnalyzeButton();

            if (data.error) {
                document.getElementById('status').textContent = data.error === 'No song playing'
                    ? 'Play a song on Spotify first!'
                    : 'Lyrics not found for this song.';
                return;
            }

            renderCard(data);
        }

        function showAnalyzeButton() {
            document.getElementById('actions').innerHTML = `
                <button class="btn analyze-btn" id="btn" onclick="fetchSong()">Analyze Current Song</button>`;
        }

        async function fetchSong() {
            const btn = document.getElementById('btn');
            const status = document.getElementById('status');
            btn.disabled = true;
            btn.textContent = 'Analyzing...';
            status.textContent = '';
            document.getElementById('card').innerHTML = '';

            const res = await fetch('/now-playing');
            const data = await res.json();

            if (data.error === 'not_logged_in') {
                window.location.href = '/login';
                return;
            }

            if (data.error) {
                status.textContent = data.error === 'No song playing'
                    ? 'Play a song on Spotify first!'
                    : 'Lyrics not found for this song.';
                btn.disabled = false;
                btn.textContent = 'Try Again';
                return;
            }

            status.textContent = '';
            renderCard(data);
            btn.disabled = false;
            btn.textContent = 'Analyze Current Song';
        }

        function renderCard(data) {
            document.getElementById('status').textContent = '';
            document.getElementById('card').innerHTML = `
                <div class="glass-card">
                    <div class="song-header">
                        <img class="album-art" src="${data.album_art}" alt="${data.title}" />
                        <div>
                            <div class="song-title">${data.title}</div>
                            <div class="song-artist">${data.artist}</div>
                        </div>
                    </div>
                    <div class="one-word">${data.one_word_summary}</div>
                    <hr class="divider">
                    <div class="section">
                        <div class="label">What it's about</div>
                        <div class="value">${data.overall_meaning}</div>
                    </div>
                    <div class="section">
                        <div class="label">Themes</div>
                        <div class="themes">${data.themes.map(t => `<span class="theme-tag">${t}</span>`).join('')}</div>
                    </div>
                    <div class="section">
                        <div class="label">Emotional Tone</div>
                        <div class="value">${data.emotional_tone}</div>
                    </div>
                    <div class="section">
                        <div class="label">Hidden Meaning</div>
                        <div class="value">${data.hidden_meaning}</div>
                    </div>
                    <div class="section">
                        <div class="label">Most Powerful Line</div>
                        <div class="value">${data.most_powerful_line}</div>
                    </div>
                </div>`;
        }

        init();
    </script>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)