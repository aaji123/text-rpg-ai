# Text RPG AI

A local-first, single-player RPG companion. Campaigns are stored as structured JSON and readable Markdown files on your computer. `state.json` is the source of truth for character identity, stats, inventory, realm progress, goals, and plot pillars; the backend regenerates Markdown summaries from it. Before narration, the backend gathers this state, campaign settings, and recent events. Your story files stay on your machine unless you choose to share the story folder. Narrator messages, brainstorm ideas, and world-field example requests are sent to Groq for a response.

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

Campaigns are created under `data/stories/`. Each campaign has `state.json` (the source of truth), generated `character_state.md`, `goals.md`, `plot_pillars.md`, `story.md`, `settings.json`, and timestamped Markdown events under `sessions/`. State includes inventory counts, realm progress, NPC relationships, confirmed lore, and learned techniques. The setup wizard lets you choose a genre, background, stat allocation, starting items, starting plane, realm ladder, highest power level, house rules, tone, and play mode. The Xianxia template includes the staged cultivation ladder from Mortal/Beginner through Origin Ancestor; custom hierarchies can be pasted and edited. The narrator receives the world ceiling and rules with every turn. It may update NPC, lore, and technique records through a bounded JSON response field; stats and items stay under backend game logic. Back up or share a campaign by copying its folder. The `data/` directory is excluded from Git to keep personal stories out of source control.

The home screen supports creating, continuing, importing, exporting, and deleting campaigns. Imports accept campaign ZIP archives created by the app; the backend checks archive paths, symlinks, file counts, and size limits and only copies supported campaign files. Example text for world-building fields is generated with the selected genre and world settings. Background templates are hard-coded in the frontend and do not use Groq. Use the theme button in the header to switch between dark and light mode.

The narrator follows the wizard's exact starting location and background. It sends immersive prose separately from optional suggested-action buttons, so you can click a suggestion or type any action of your own. Use `/roll 1d20` for an unopposed roll or `/roll 1d20 vs 15` to log a target and explicit success or failure; failed checks prompt the narrator to introduce a proportionate complication. Use `/recap` or the **Recap** button to summarize recent events. Prefix a question with `/ooc` to ask about rules or campaign details without advancing the story. The narrator introduces a subtle world tick every six in-world turns and suggests a session break with a continuity summary every twelve turns.
