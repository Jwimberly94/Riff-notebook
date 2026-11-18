# Riff Notebook

A local Flask app for recording guitar ideas, attaching details, and browsing saved riffs.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`. Microphone recording requires localhost or HTTPS and browser permission.

Audio and SQLite data are stored in `instance/`.
