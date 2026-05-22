# 🎵 Song Meaning Analyzer

A web app that detects what you're currently playing on Spotify and uses AI to analyze the deeper meaning of the song in real time.

## What it does

- Detects your currently playing Spotify track
- Fetches lyrics automatically via lrclib.net
- Uses AI to analyze the song's meaning, themes, emotional tone, hidden meaning, and most powerful line
- Beautiful glassmorphism UI, fully mobile friendly

## Tech Stack

- **Backend** — FastAPI + Python
- **AI** — Strands Agents + OpenRouter (GPT)
- **Lyrics** — lrclib.net (free, no API key needed)
- **Music** — Spotify Web API

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/song-meaning-analyzer.git
cd song-meaning-analyzer
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Set up environment variables

Create a `.env` file in the root folder:


### 4. Get your API keys

- **Spotify** — [developer.spotify.com](https://developer.spotify.com/dashboard) → create an app
- **OpenRouter** — [openrouter.ai/keys](https://openrouter.ai/keys) → free account

### 5. Run the app

```bash
uv run app.py
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

On first run, Spotify will ask you to log in and approve access — just copy the redirect URL back into the terminal.

## Usage

1. Play any song on Spotify
2. Open the app and hit **Analyze Current Song**
3. Get a deep AI-powered breakdown of the song's meaning

## Note

This app is in Spotify development mode, which allows up to 5 users. To add users, go to your Spotify app dashboard → Settings → User Management.

## License

MIT