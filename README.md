# Text RPG AI

Text RPG AI is a local, single-player storytelling game. You describe what your
character tries to do, and an AI narrator describes what happens next. You can shape
the world and character before play begins, then guide the story one action at a time.

This guide starts with the steps for playing. Technical details are collected at the
end for anyone who wants to understand or change how the app is built.

## What happens to my story?

Think of each campaign as a folder on your computer. The app saves your character,
items, goals, and world details there, along with a readable record of what happened.
You can copy or export a campaign folder as a backup or share it with someone else.

Your campaign files stay on this computer unless you choose to share or export them.
When you ask the narrator for a response, the app sends your message and the relevant
campaign context to Groq so it can generate the reply. Brainstorming and generated
examples are sent there too. Your Groq API key is kept in a private `.env` file and
should never be shared.

## What you need

- A computer with Python 3.10 or newer
- Node.js 18 or newer (npm is included with Node.js)
- A free Groq account and API key
- An internet connection when you want an AI response

## First-time setup on Windows

### 1. Get a Groq API key

Create an account at [console.groq.com](https://console.groq.com/). In the Groq
console, open **API Keys**, create a key, and copy it. Treat the key like a password.

### 2. Save the key privately

In the project folder, make a copy of `.env.example` named `.env`. Open `.env` in a
text editor and paste your key after `GROQ_API_KEY=`. Save the file. Keep `.env`
private; it is excluded from Git and should not be sent to anyone.

The app currently uses Groq's `qwen/qwen3.8-27b` model by default. You do not need to
change it to get started.

### 3. Start the story service

Open PowerShell in the project folder and run these commands one at a time:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Keep this PowerShell window open while you play. The first command creates a private
Python environment for this app. The second installs the backend pieces it needs. The
third starts the local service that saves campaigns and talks to Groq.

### 4. Start the game window

Open a second PowerShell window in the project folder and run:

```powershell
cd frontend
npm install
npm run dev
```

Keep this window open too. Open the local web address printed in the window; it is
usually `http://127.0.0.1:5173`. The app runs in your browser, but its story files are
saved locally by the backend.

## Playing your first campaign

On the home page, choose **Create a campaign**. The setup walks you through the world,
opening situation, character, and starting items. You can use the example buttons for
ideas, or write your own details. Choose a place where the story begins; the narrator
uses that location as the starting point.

When the story opens, type what your character attempts in the message box. For
example: “I ask the shopkeeper whether anyone came through here last night.” You can
click one of the suggested actions or type something entirely different. The character
sheet shows your saved stats, items, current in-world time, weather, and known faction
standing.

The app saves each turn and dice roll as it happens. You can return to the home page
by clicking **MYTHOS** in the upper-left corner, then continue a recent campaign or
load another one. Use the theme button to switch between dark and light appearance.

## Commands you can type

- `/help` shows the command guide.
- `/stats` shows character stats, realm, and resource levels. `/status` works too.
- `/inventory` shows saved items and their quantities or durability.
- `/recap` summarizes recent events. The **Recap** button does the same thing.
- `/ooc Is this action allowed?` asks a rules or world question without advancing
  the story.
- `/roll 1d20` rolls a die. To compare against a target, use `/roll 1d20 vs 15`.

Dice are rolled and recorded by the app, so the narrator cannot change the result. In
dice-focused play, a failed check should lead to a complication that keeps the story
moving.

## Backing up, importing, or sharing a campaign

Campaigns are stored in `data/stories/`, with one folder per campaign. Use the app's
export option to make a shareable ZIP archive. You can import an archive from another
player through the home page. The app checks imported files before adding them to your
local library. Sharing or exporting a campaign shares its story contents, so review
the files before sending them to someone else.

## If something goes wrong

- **The page does not open:** Check that both PowerShell windows are still running.
  Use the local web address printed by the frontend window.
- **The narrator cannot respond:** Check that `.env` exists in the project folder and
  that `GROQ_API_KEY=` has a valid key after the equals sign. Also check your internet
  connection and Groq account.
- **The key was exposed:** Revoke it in the Groq console, create a new one, and update
  `.env`.
- **You want a clean restart:** Stop a running service with `Ctrl+C` in its PowerShell
  window, then run its start command again.

## Technical information

### How the pieces work together

The React app in `frontend/` displays the home page, campaign setup, chat, character
sheet, and settings. It sends requests to the local FastAPI service in `backend/`.
Before a narrator request, the backend gathers the campaign's structured state,
settings, active goals, plot pillars, and recent Markdown session events. It sends the
request and this context to Groq, then records the response and any supported state
updates.

### Storage and state

Each campaign folder under `data/stories/` contains:

- `state.json`: authoritative character, inventory, realm, world clock, weather,
  relationships, lore, techniques, and faction reputation data.
- `settings.json`: campaign preferences such as genre, difficulty, tone, and mode.
- Generated Markdown summaries such as `character_state.md`, `goals.md`, and
  `plot_pillars.md`.
- `sessions/`: timestamped Markdown logs of conversation turns and dice rolls.

The backend reads JSON for game logic and regenerates the readable Markdown summaries
from it. Markdown is intended for browsing; JSON remains the source of truth.

### Project layout

```text
backend/
  ai/             Groq client, narrator prompts, and response parsing
  api/            FastAPI routes and shared dependencies
  mcp_server/     Game-state context builder
  storage/        Campaign folders, JSON state, and Markdown logs
  utils/          Dice rolling and supporting utilities
  app.py          FastAPI application and middleware
frontend/
  src/            React views, components, styles, and API service
data/stories/     Local campaign files created at runtime
```

### Configuration

Runtime settings are loaded from `.env` by `backend/config.py`. Available values in
`.env.example` include:

- `GROQ_API_KEY`: secret key for Groq; do not commit or share it.
- `GROQ_MODEL`: model name; default is `qwen/qwen3.8-27b`.
- `APP_HOST` and `APP_PORT`: local backend address; defaults are `127.0.0.1` and
  `8000`.
- `STORIES_DIR`: campaign storage location; default is `./data/stories`.

Python dependencies are listed in `backend/requirements.txt`. Frontend dependencies
and commands are defined in `frontend/package.json`. The local FastAPI documentation
is available at `http://127.0.0.1:8000/docs` while the backend is running.
