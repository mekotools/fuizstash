"""Kopplung an den Teilen-Speicher von fuiz.

fuiz legt geteilte Quizze in der Tabelle `kv_share` ab (Spalten `key`, `value`,
`expires_at`). Diese Datei liest daraus (lesend) und schreibt ausschließlich
eigene, fristlose Einträge für die Übernahme in den Browser.

Regeln, die hier gelten:
* Lesen und Schreiben getrennt: Lesen über eine read-only-Verbindung.
* Nie fremde Zeilen ändern oder löschen — nur einfügen und eigene Zeilen wieder
  entfernen.
* Fehlt die erwartete Struktur, wird das sichtbar gemeldet (kein stiller Fehler).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

TABELLE = "kv_share"
SPALTEN = ("key", "value", "expires_at")


class SpeicherFehler(RuntimeError):
    """Der Teilen-Speicher ist nicht benutzbar — mit Klartextgrund."""


@dataclass
class Kopplungslage:
    pfad: str
    vorhanden: bool
    tabelle_ok: bool
    schreibbar: bool
    hinweis: str

    @property
    def gesund(self) -> bool:
        return self.vorhanden and self.tabelle_ok and self.schreibbar


def pfad() -> str:
    return os.environ.get("FUIZ_KV", "")


def _jetzt_sekunden() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _lesend() -> sqlite3.Connection:
    ziel = pfad()
    if not ziel or not os.path.exists(ziel):
        raise SpeicherFehler(
            "Der Teilen-Speicher von fuiz ist nicht eingebunden "
            "(Pfad fehlt). Einreichen ist deshalb nicht möglich."
        )
    return sqlite3.connect(f"file:{ziel}?mode=ro", uri=True, timeout=10)


def _schreibend() -> sqlite3.Connection:
    ziel = pfad()
    if not ziel or not os.path.exists(ziel):
        raise SpeicherFehler(
            "Der Teilen-Speicher von fuiz ist nicht eingebunden "
            "(Pfad fehlt). Übergeben ist deshalb nicht möglich."
        )
    verbindung = sqlite3.connect(ziel, timeout=15)
    verbindung.execute("PRAGMA journal_mode = WAL")
    return verbindung


def kopplung_pruefen(probe_schreiben: bool = True) -> Kopplungslage:
    """Prüft die Kopplung. Mit `probe_schreiben` wird ein eigener Probeeintrag
    mit kurzer Frist angelegt und sofort wieder entfernt — der einzige
    verlässliche Nachweis, dass Schreiben wirklich geht."""
    ziel = pfad()
    if not ziel or not os.path.exists(ziel):
        return Kopplungslage(ziel, False, False, False,
                             "Teilen-Speicher nicht eingebunden")
    try:
        with _lesend() as v:
            spalten = [z[1] for z in v.execute(f"PRAGMA table_info({TABELLE})")]
        if not spalten:
            return Kopplungslage(ziel, True, False, False,
                                 f"Tabelle {TABELLE} fehlt (fuiz-Update?)")
        if not set(SPALTEN).issubset(set(spalten)):
            return Kopplungslage(ziel, True, False, False,
                                 f"Spalten weichen ab: {sorted(spalten)}")
    except sqlite3.Error as fehler:
        return Kopplungslage(ziel, True, False, False, f"nicht lesbar: {fehler}")

    schreibbar = False
    hinweis = "bereit"
    if probe_schreiben:
        probe = str(uuid.uuid4())
        try:
            with _schreibend() as s:
                s.execute(
                    f"INSERT INTO {TABELLE} (key, value, expires_at) VALUES (?, ?, ?)",
                    (probe, "{}", _jetzt_sekunden() + 60),
                )
                s.commit()
                s.execute(f"DELETE FROM {TABELLE} WHERE key = ?", (probe,))
                s.commit()
            schreibbar = True
        except sqlite3.Error as fehler:
            hinweis = f"nicht beschreibbar: {fehler}"
    else:
        schreibbar = os.access(ziel, os.W_OK)
        hinweis = "Schreiben nicht geprüft" if not schreibbar else "bereit"
    return Kopplungslage(ziel, True, True, schreibbar, hinweis)


def inhalt_holen(kennung: str) -> str | None:
    """Liest einen Teilen-Eintrag. Gibt None zurück, wenn er unbekannt oder
    abgelaufen ist."""
    try:
        with _lesend() as v:
            zeile = v.execute(
                f"SELECT value FROM {TABELLE} WHERE key = ? "
                "AND (expires_at IS NULL OR expires_at > ?)",
                (kennung, _jetzt_sekunden()),
            ).fetchone()
    except sqlite3.Error as fehler:
        raise SpeicherFehler(f"Teilen-Speicher nicht lesbar: {fehler}") from fehler
    return zeile[0] if zeile else None


def pruefe_inhalt(roh: str) -> dict:
    """Prüft, dass der Inhalt ein fuiz-Quiz ist. Gibt ihn als Objekt zurück."""
    try:
        daten = json.loads(roh)
    except json.JSONDecodeError as fehler:
        raise SpeicherFehler(f"Inhalt ist kein lesbares JSON: {fehler}") from fehler
    if not isinstance(daten, dict):
        raise SpeicherFehler("Inhalt ist kein Quiz-Objekt.")
    if not isinstance(daten.get("title"), str) or not daten["title"].strip():
        raise SpeicherFehler("Dem Inhalt fehlt der Titel.")
    if not isinstance(daten.get("slides"), list):
        raise SpeicherFehler("Dem Inhalt fehlt die Fragenliste (slides).")
    return daten


def uebernahme_eintragen(inhalt: str, kennung: str | None = None) -> str:
    """Legt einen dauerhaften Eintrag (ohne Frist) an und gibt die Kennung zurück."""
    schluessel = (kennung or str(uuid.uuid4())).lower()
    if not re.match(r"^[0-9a-f-]{36}$", schluessel):
        raise SpeicherFehler("Ungültige Kennung für den Übernahme-Eintrag.")
    try:
        with _schreibend() as s:
            s.execute(
                f"INSERT INTO {TABELLE} (key, value, expires_at) VALUES (?, ?, NULL) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, expires_at = NULL",
                (schluessel, inhalt),
            )
            s.commit()
    except sqlite3.Error as fehler:
        raise SpeicherFehler(f"Übernahme-Eintrag nicht schreibbar: {fehler}") from fehler
    return schluessel


def uebernahme_entfernen(kennung: str) -> bool:
    """Entfernt genau den eigenen Übernahme-Eintrag. Fremde Zeilen bleiben unberührt."""
    try:
        with _schreibend() as s:
            cursor = s.execute(f"DELETE FROM {TABELLE} WHERE key = ?", (kennung.lower(),))
            s.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as fehler:
        raise SpeicherFehler(f"Übernahme-Eintrag nicht entfernbar: {fehler}") from fehler


def uebernahme_vorhanden(kennung: str) -> bool:
    try:
        with _lesend() as v:
            zeile = v.execute(
                f"SELECT 1 FROM {TABELLE} WHERE key = ?", (kennung.lower(),)
            ).fetchone()
    except sqlite3.Error:
        return False
    return zeile is not None
