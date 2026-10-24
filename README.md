# Text RPG AI

A local-first, single-player RPG companion. Campaigns are stored as readable Markdown and JSON files on your computer. When you send an action, the backend gathers your character sheet, active goals, campaign settings, plot pillars, and recent events before asking Groq for the next narration. Your story files stay on your machine unless you choose to share the story folder. Narrator messages and any premise you submit to the optional brainstorm feature are sent to Groq for a response.

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer (includes npm)
- A free Groq account and API key

## Configure your Groq key

Create a free account at [console.groq.com](https://console.groq.com/), open **API Keys**, and create a key. Copy `.env.example` to `.env` in the project root, then paste the key after `GROQ_API_KEY=`. Keep `.env` private; it is excluded from Git. The default model is `qwen/qwen3.8-27b`.

## Install and run

Open two terminals in the project folder.

### Backend (terminal 1)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks virtual environment activation, run the commands below instead (the final command uses the environment interpreter directly):

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

### Frontend (terminal 2)

```powershell
cd frontend
npm install
npm run dev
```

Open the local address printed by Vite (normally `http://127.0.0.1:5173`). The backend API docs are at `http://127.0.0.1:8000/docs`.

## Story files

Campaigns are created under `data/stories/`. Each campaign has a template-specific `character_state.md`, `goals.md`, `plot_pillars.md`, `story.md`, `settings.json`, and a `sessions/` directory of timestamped Markdown events. The settings include the selected world template and world power level. Back up or share a campaign by copying its folder. The `data/` directory is excluded from Git to keep personal stories out of source control.

Use `/roll 1d20` or `/roll 2d6+3` in the chat input to save a dice result into the campaign history.
