DragonBotV2
=============

A lightweight Lichess bot framework written in Python. This repository contains a chess engine wrapper, Lichess integration, matchmaking and time-management helpers with a pluggable engine architecture.

Quick overview
--------------
- Purpose: run an automated bot that can play games on Lichess (or be used as a local engine harness).
- Main entrypoint: `main.py` (project root)
- Important directories:
  - `engines/` — engine implementations and helpers (e.g. `dragonbot.py`, `opening.py`)
  - `lib/` — core library code (Lichess client, matchmaking, models, config helpers)

Requirements
------------
- Python 3.8+
- A working internet connection for Lichess integration (unless running in local/offline mode)
- Dependencies listed in `requirements.txt`

Installation (Windows PowerShell)
---------------------------------
1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

Configuration
-------------
- Copy the example config: `config.yml.default` -> `config.yml` and edit values as needed.

```powershell
copy-item config.yml.default config.yml
notepad config.yml
```

- Typical settings to check/enter in `config.yml`:
  - Lichess API token (if you want the bot to connect to Lichess)
  - Bot account name and game settings
  - Engine selection and engine-specific options

Running the bot
---------------
- Start the bot from the project root:

```powershell
python main.py
```

- Behavior depends on configuration in `config.yml`. If the bot connects to Lichess it will listen for incoming challenges / pairings depending on the matchmaking settings.

Files of interest
-----------------
- `main.py` — application entrypoint and runtime orchestration.
- `config.yml.default` — example configuration used as a template.
- `engines/dragonbot.py` — primary engine implementation for the project.
- `lib/lichess_bot.py` and `lib/lichess.py` — Lichess API integration and types.
- `lib/matchmaking.py`, `lib/time_manager.py`, `engines/time_manager.py` — utilities for pairing and time control.

Development notes
-----------------
- Add or extend engine implementations under `engines/`.
- Core logic lives in `lib/`. Keep Lichess-specific code isolated from engine code where possible to make testing easier.

Troubleshooting and tips
------------------------
- If the bot doesn't start, verify Python and virtual environment activation.
- Check `config.yml` exists and contains valid values. If you only have `config.yml.default`, copy it to `config.yml` before running.
- If Lichess connection fails, verify the API token and network connectivity.



