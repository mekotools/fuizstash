"""Datenhaltung der Fuizstash (SQLite, ein Prozess, keine Fremddienste)."""

from __future__ import annotations

import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS quiz (
    id TEXT PRIMARY KEY,
    nutzer TEXT NOT NULL,
    nutzer_mail TEXT,
    titel TEXT NOT NULL,
    fragen INTEGER NOT NULL,
    groesse INTEGER NOT NULL,
    herkunft TEXT NOT NULL,
    herkunft_ref TEXT,
    inhalt TEXT NOT NULL,
    uebernahme_kennung TEXT,
    erstellt_am TEXT NOT NULL,
    geaendert_am TEXT NOT NULL,
    geloescht_am TEXT,
    ersetzt_anzahl INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_quiz_nutzer ON quiz (nutzer, geloescht_am);

CREATE TABLE IF NOT EXISTS ereignis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zeit TEXT NOT NULL,
    nutzer TEXT,
    quiz_id TEXT,
    art TEXT NOT NULL,
    text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS einstellung (
    schluessel TEXT PRIMARY KEY,
    wert TEXT NOT NULL,
    geaendert_am TEXT NOT NULL
);
"""

VORGABEN = {
    "max_quiz_mb": "25",
    "max_nutzer_mb": "250",
    "papierkorb_tage": "30",
}

BESCHREIBUNG = {
    "max_quiz_mb": "Größte zulässige Größe eines eingereichten Quiz in Megabyte",
    "max_nutzer_mb": "Belegter Speicher je Person, ab dem weitere Einreichungen abgelehnt werden",
    "papierkorb_tage": "Nach wie vielen Tagen gelöschte Einträge endgültig verschwinden",
}


@dataclass
class Quiz:
    id: str
    titel: str
    fragen: int
    groesse: int
    herkunft: str
    herkunft_ref: str | None
    erstellt_am: str
    geaendert_am: str
    geloescht_am: str | None
    ersetzt_anzahl: int
    uebernahme_kennung: str | None
    inhalt: str = ""

    @property
    def im_papierkorb(self) -> bool:
        return self.geloescht_am is not None


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def pfad() -> str:
    return os.environ.get("FUIZSTASH_DATEN", "/daten/fuizstash.db")


def verbinden() -> sqlite3.Connection:
    ziel = pfad()
    ordner = os.path.dirname(ziel)
    if ordner:
        os.makedirs(ordner, exist_ok=True)
    verbindung = sqlite3.connect(ziel, timeout=15)
    verbindung.row_factory = sqlite3.Row
    verbindung.execute("PRAGMA journal_mode = WAL")
    verbindung.execute("PRAGMA foreign_keys = ON")
    return verbindung


def einrichten() -> None:
    with verbinden() as v:
        v.executescript(SCHEMA)
        for schluessel, wert in VORGABEN.items():
            v.execute(
                "INSERT OR IGNORE INTO einstellung (schluessel, wert, geaendert_am) "
                "VALUES (?, ?, ?)",
                (schluessel, wert, _jetzt()),
            )


def einstellungen() -> dict[str, str]:
    with verbinden() as v:
        zeilen = v.execute("SELECT schluessel, wert FROM einstellung").fetchall()
    werte = dict(VORGABEN)
    werte.update({z["schluessel"]: z["wert"] for z in zeilen})
    return werte


def einstellungen_setzen(werte: dict[str, str]) -> list[str]:
    """Setzt Einstellungen und gibt die übernommenen Schlüssel zurück."""
    uebernommen = []
    with verbinden() as v:
        for schluessel, wert in werte.items():
            if schluessel not in VORGABEN:
                continue
            v.execute(
                "INSERT INTO einstellung (schluessel, wert, geaendert_am) VALUES (?, ?, ?) "
                "ON CONFLICT(schluessel) DO UPDATE SET wert = excluded.wert, "
                "geaendert_am = excluded.geaendert_am",
                (schluessel, str(wert), _jetzt()),
            )
            uebernommen.append(schluessel)
    return uebernommen


def ereignis(art: str, text: str, nutzer: str | None = None, quiz_id: str | None = None) -> None:
    with verbinden() as v:
        v.execute(
            "INSERT INTO ereignis (zeit, nutzer, quiz_id, art, text) VALUES (?, ?, ?, ?, ?)",
            (_jetzt(), nutzer, quiz_id, art, text),
        )


def ereignisse(nutzer: str, grenze: int = 20) -> list[sqlite3.Row]:
    with verbinden() as v:
        return v.execute(
            "SELECT zeit, art, text FROM ereignis WHERE nutzer = ? ORDER BY id DESC LIMIT ?",
            (nutzer, grenze),
        ).fetchall()


def _zeile_zu_quiz(zeile: sqlite3.Row, mit_inhalt: bool = False) -> Quiz:
    return Quiz(
        id=zeile["id"],
        titel=zeile["titel"],
        fragen=zeile["fragen"],
        groesse=zeile["groesse"],
        herkunft=zeile["herkunft"],
        herkunft_ref=zeile["herkunft_ref"],
        erstellt_am=zeile["erstellt_am"],
        geaendert_am=zeile["geaendert_am"],
        geloescht_am=zeile["geloescht_am"],
        ersetzt_anzahl=zeile["ersetzt_anzahl"],
        uebernahme_kennung=zeile["uebernahme_kennung"],
        inhalt=zeile["inhalt"] if mit_inhalt else "",
    )


def liste(nutzer: str, papierkorb: bool = False) -> list[Quiz]:
    with verbinden() as v:
        if papierkorb:
            zeilen = v.execute(
                "SELECT * FROM quiz WHERE nutzer = ? AND geloescht_am IS NOT NULL "
                "ORDER BY geloescht_am DESC",
                (nutzer,),
            ).fetchall()
        else:
            zeilen = v.execute(
                "SELECT * FROM quiz WHERE nutzer = ? AND geloescht_am IS NULL "
                "ORDER BY geaendert_am DESC",
                (nutzer,),
            ).fetchall()
    return [_zeile_zu_quiz(z) for z in zeilen]


def holen(nutzer: str, quiz_id: str, mit_inhalt: bool = True) -> Quiz | None:
    with verbinden() as v:
        zeile = v.execute(
            "SELECT * FROM quiz WHERE id = ? AND nutzer = ?", (quiz_id, nutzer)
        ).fetchone()
    return _zeile_zu_quiz(zeile, mit_inhalt) if zeile else None


def nach_titel(nutzer: str, titel: str) -> Quiz | None:
    with verbinden() as v:
        zeile = v.execute(
            "SELECT * FROM quiz WHERE nutzer = ? AND titel = ? AND geloescht_am IS NULL",
            (nutzer, titel),
        ).fetchone()
    return _zeile_zu_quiz(zeile) if zeile else None


def belegung(nutzer: str) -> int:
    with verbinden() as v:
        zeile = v.execute(
            "SELECT COALESCE(SUM(groesse), 0) AS gesamt FROM quiz WHERE nutzer = ? "
            "AND geloescht_am IS NULL",
            (nutzer,),
        ).fetchone()
    return int(zeile["gesamt"])


def anlegen(
    nutzer: str,
    nutzer_mail: str | None,
    titel: str,
    fragen: int,
    inhalt: str,
    herkunft: str,
    herkunft_ref: str | None,
) -> str:
    kennung = str(uuid.uuid4())
    jetzt = _jetzt()
    with verbinden() as v:
        v.execute(
            "INSERT INTO quiz (id, nutzer, nutzer_mail, titel, fragen, groesse, herkunft, "
            "herkunft_ref, inhalt, erstellt_am, geaendert_am) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (kennung, nutzer, nutzer_mail, titel, fragen, len(inhalt.encode()),
             herkunft, herkunft_ref, inhalt, jetzt, jetzt),
        )
    return kennung


def ersetzen(nutzer: str, quiz_id: str, fragen: int, inhalt: str, herkunft_ref: str | None) -> None:
    """Ersetzt den Inhalt eines vorhandenen Eintrags (keine Versionen in Stufe 1)."""
    with verbinden() as v:
        v.execute(
            "UPDATE quiz SET fragen = ?, groesse = ?, inhalt = ?, herkunft_ref = ?, "
            "geaendert_am = ?, ersetzt_anzahl = ersetzt_anzahl + 1 WHERE id = ? AND nutzer = ?",
            (fragen, len(inhalt.encode()), inhalt, herkunft_ref, _jetzt(), quiz_id, nutzer),
        )


def uebernahme_setzen(nutzer: str, quiz_id: str, kennung: str) -> None:
    with verbinden() as v:
        v.execute(
            "UPDATE quiz SET uebernahme_kennung = ? WHERE id = ? AND nutzer = ?",
            (kennung, quiz_id, nutzer),
        )


def loeschen(nutzer: str, quiz_id: str) -> bool:
    with verbinden() as v:
        cursor = v.execute(
            "UPDATE quiz SET geloescht_am = ? WHERE id = ? AND nutzer = ? "
            "AND geloescht_am IS NULL",
            (_jetzt(), quiz_id, nutzer),
        )
        return cursor.rowcount > 0


def wiederherstellen(nutzer: str, quiz_id: str) -> bool:
    with verbinden() as v:
        cursor = v.execute(
            "UPDATE quiz SET geloescht_am = NULL WHERE id = ? AND nutzer = ? "
            "AND geloescht_am IS NOT NULL",
            (quiz_id, nutzer),
        )
        return cursor.rowcount > 0


def endgueltig_loeschen(nutzer: str, quiz_id: str) -> bool:
    with verbinden() as v:
        cursor = v.execute("DELETE FROM quiz WHERE id = ? AND nutzer = ?", (quiz_id, nutzer))
        if cursor.rowcount:
            v.execute(
                "DELETE FROM ereignis WHERE quiz_id = ? AND nutzer = ?", (quiz_id, nutzer)
            )
        return cursor.rowcount > 0


def papierkorb_raeumen() -> int:
    """Entfernt Einträge, deren Papierkorbzeit abgelaufen ist, und verdichtet."""
    tage = int(einstellungen().get("papierkorb_tage", VORGABEN["papierkorb_tage"]))
    grenze = datetime.now(timezone.utc) - timedelta(days=tage)
    with verbinden() as v:
        zeilen = v.execute(
            "SELECT id, nutzer, uebernahme_kennung FROM quiz "
            "WHERE geloescht_am IS NOT NULL AND geloescht_am < ?",
            (grenze.isoformat(timespec="seconds"),),
        ).fetchall()
    entfernt = 0
    for zeile in zeilen:
        if endgueltig_loeschen(zeile["nutzer"], zeile["id"]):
            entfernt += 1
            if zeile["uebernahme_kennung"]:
                uebernahme_entfernen(zeile["uebernahme_kennung"])
    if entfernt:
        verdichten()
    return entfernt


def uebernahme_entfernen(kennung: str) -> bool:
    """Kleine Brücke, damit die Datenbank keine fuiz-Kenntnis braucht."""
    from . import fuizspeicher

    try:
        return fuizspeicher.uebernahme_entfernen(kennung)
    except fuizspeicher.SpeicherFehler as fehler:
        ereignis("kopplung", f"Übernahme-Eintrag {kennung} nicht entfernbar: {fehler}")
        return False


def verdichten() -> None:
    with verbinden() as v:
        v.execute("VACUUM")


def warten(sekunden: float = 0.01) -> None:
    """Nur für Tests: kurz warten, damit Zeitstempel sich unterscheiden."""
    time.sleep(sekunden)
