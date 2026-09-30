# Tsundere Girlfriend Chat (Mika)

A DM-style popup chat window (Tkinter) with a tsundere AI girlfriend powered by Gemini,
selectable text-to-speech voices (edge-tts), and swappable profile pictures.

## Install & run

Windows (PowerShell / CMD):
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    copy .env.example .env
    (open .env and paste your GEMINI_API_KEY)
    python main.py

macOS / Linux:
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    (open .env and paste your GEMINI_API_KEY)
    python3 main.py

Linux only, if Tkinter is missing:  sudo apt install python3-tk

## Customising
- Profile pictures: drop any .png/.jpg into `avatars/` (they appear in the dropdown), or use the Upload button.
- Regenerate the built-in drawn avatars: `python make_avatars.py`
- Voices: edit VOICE_PRESETS in voice.py. List all voices with `edge-tts --list-voices`.
- Personality: edit personality.py.
- Model/parameters: edit .env (GEMINI_MODEL, TEMPERATURE, TOP_P ...).
- Other AI providers: replace the body of TsundereBrain in ai_client.py; keep the `reply(text)` method.
