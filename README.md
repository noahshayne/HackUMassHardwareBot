# HackUMassHardwareBot — Discord bot setup

This repository contains a minimal Discord bot setup using discord.py and python-dotenv.

Quick start (Windows PowerShell):

1. Create and activate a virtual environment (optional)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Create a `.env` file from the example and add your bot token

```powershell
cp .env.example .env
# then edit .env and set DISCORD_TOKEN=your_token_here
```

4. Run the bot from the repository root

```powershell
python -m HackUMassHardwareBot.main
```


