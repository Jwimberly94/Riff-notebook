from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
ALLOWED_AUDIO_EXTENSIONS = {"webm", "wav", "mp3", "m4a", "ogg", "mp4"}


# Create and configure the Flask application and its database-backed routes.
def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-riffbook-session-key")
    app.config["DATABASE"] = str(BASE_DIR / "instance" / "riffs.sqlite3")
    app.config["UPLOAD_FOLDER"] = str(BASE_DIR / "instance" / "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    # Open the SQLite database and configure rows to behave like dictionaries.
    def connect_db() -> sqlite3.Connection:
        connection = sqlite3.connect(app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        return connection

    with connect_db() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS riffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                tuning TEXT NOT NULL DEFAULT 'Standard',
                bpm INTEGER,
                musical_key TEXT NOT NULL DEFAULT '',
                mood TEXT NOT NULL DEFAULT 'Unsorted',
                notes TEXT NOT NULL DEFAULT '',
                audio_filename TEXT NOT NULL
            )"""
        )

    # Display saved riffs and apply optional text and mood filters.
    @app.get("/")
    def index():
        query = request.args.get("q", "").strip()
        mood = request.args.get("mood", "").strip()
        with connect_db() as connection:
            sql = "SELECT * FROM riffs WHERE 1 = 1"
            values: list[str] = []
            if query:
                sql += " AND (title LIKE ? OR notes LIKE ? OR musical_key LIKE ? OR tuning LIKE ?)"
                term = f"%{query}%"
                values.extend([term, term, term, term])
            if mood:
                sql += " AND mood = ?"
                values.append(mood)
            sql += " ORDER BY created_at DESC, id DESC"
            riffs = connection.execute(sql, values).fetchall()
            moods = [row[0] for row in connection.execute(
                "SELECT DISTINCT mood FROM riffs ORDER BY mood COLLATE NOCASE"
            ).fetchall()]
            total = connection.execute("SELECT COUNT(*) FROM riffs").fetchone()[0]
        return render_template("index.html", riffs=riffs, query=query, mood=mood, moods=moods, total=total)

    # Validate an uploaded recording and save its metadata to the notebook.
    @app.post("/riffs")
    def create_riff():
        audio = request.files.get("audio")
        if audio is None or not audio.filename:
            flash("Record a riff before saving it.", "error")
            return redirect(url_for("index"))

        original_name = secure_filename(audio.filename)
        extension = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        if extension not in ALLOWED_AUDIO_EXTENSIONS:
            flash("That audio format is not supported. Try recording again in your browser.", "error")
            return redirect(url_for("index"))

        title = request.form.get("title", "").strip()[:100]
        if not title:
            flash("Give your riff a name before saving.", "error")
            return redirect(url_for("index"))

        bpm_value = request.form.get("bpm", "").strip()
        try:
            bpm = int(bpm_value) if bpm_value else None
            if bpm is not None and not 20 <= bpm <= 300:
                raise ValueError
        except ValueError:
            flash("Tempo must be between 20 and 300 BPM.", "error")
            return redirect(url_for("index"))

        filename = f"{uuid.uuid4().hex}.{extension}"
        audio.save(Path(app.config["UPLOAD_FOLDER"]) / filename)
        with connect_db() as connection:
            connection.execute(
                """INSERT INTO riffs (title, created_at, tuning, bpm, musical_key, mood, notes, audio_filename)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    title,
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    request.form.get("tuning", "Standard")[:40],
                    bpm,
                    request.form.get("musical_key", "")[:20],
                    request.form.get("mood", "Unsorted")[:40],
                    request.form.get("notes", "").strip()[:2000],
                    filename,
                ),
            )
        flash("Riff saved to your notebook.", "success")
        return redirect(url_for("index"))

    # Delete a saved riff and remove its uploaded audio file.
    @app.post("/riffs/<int:riff_id>/delete")
    def delete_riff(riff_id: int):
        with connect_db() as connection:
            riff = connection.execute("SELECT audio_filename FROM riffs WHERE id = ?", (riff_id,)).fetchone()
            if riff is None:
                abort(404)
            connection.execute("DELETE FROM riffs WHERE id = ?", (riff_id,))
        audio_path = Path(app.config["UPLOAD_FOLDER"]) / riff["audio_filename"]
        audio_path.unlink(missing_ok=True)
        flash("Riff removed.", "success")
        return redirect(url_for("index"))

    # Serve an uploaded audio file for browser playback.
    @app.get("/audio/<path:filename>")
    def audio_file(filename: str):
        if Path(filename).name != filename:
            abort(404)
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
