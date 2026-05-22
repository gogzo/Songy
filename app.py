import os
import json
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from strands import Agent
from strands.models.openai import OpenAIModel

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope="user-read-currently-playing"
))

model = OpenAIModel(
    client_args={
        "api_key": OPENROUTER_KEY,
        "base_url": "https://openrouter.ai/api/v1"
    },
    model_id="openai/gpt-oss-120b:free",
)
agent = Agent(model=model)

app = FastAPI()

def get_current_song():
    try:
        current = sp.current_user_playing_track()
        if current and current["is_playing"]:
            track = current["item"]
            return {
                "title": track["name"],
                "artist": track["artists"][0]["name"],
                "album_art": track["album"]["images"][0]["url"]
            }
    except:
        pass
    return None

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

@app.get("/now-playing")
def now_playing():
    song = get_current_song()
    if not song:
        return {"error": "No song playing"}
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
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
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
        .album-placeholder {
            width: 72px;
            height: 72px;
            border-radius: 12px;
            background: linear-gradient(135deg, #7F77DD, #1D9E75);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            font-size: 1.5rem;
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
        .analyze-btn {
            width: 100%;
            max-width: 480px;
            margin-top: 1rem;
            padding: 0.9rem;
            background: rgba(127,119,221,0.2);
            border: 0.5px solid rgba(127,119,221,0.4);
            border-radius: 50px;
            color: #CECBF6;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
        }
        .analyze-btn:hover { background: rgba(127,119,221,0.35); }
        .analyze-btn:disabled { opacity: 0.5; cursor: not-allowed; }
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
    <div id="status">Play a song on Spotify to get started</div>
    <div id="card"></div>
    <button class="analyze-btn" onclick="fetchSong()" id="btn">Analyze Current Song</button>

    <script>
        async function fetchSong() {
            const btn = document.getElementById('btn');
            const status = document.getElementById('status');
            btn.disabled = true;
            btn.textContent = 'Analyzing...';
            status.textContent = 'Fetching your song...';
            document.getElementById('card').innerHTML = '';

            try {
                const res = await fetch('/now-playing');
                const data = await res.json();

                if (data.error) {
                    status.textContent = data.error === 'No song playing'
                        ? 'Play a song on Spotify first!'
                        : 'Lyrics not found for this song.';
                    btn.disabled = false;
                    btn.textContent = 'Try Again';
                    return;
                }

                status.textContent = '';
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

                btn.disabled = false;
                btn.textContent = 'Analyze Current Song';

            } catch(e) {
                status.textContent = 'Something went wrong. Try again.';
                btn.disabled = false;
                btn.textContent = 'Try Again';
            }
        }
    </script>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)