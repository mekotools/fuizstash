"""Prüfungen der Fuizstash.

Aufbau: je Test eine eigene Ablage-Datenbank und ein eigener fuiz-Teilenspeicher.
Geprüft wird das Verhalten an den Rändern — ohne Anmeldung, getrennte Bestände,
Übernahme, Papierkorb, Grenzen, gestörte Kopplung.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

KOPF_A = {"remote-user": "lehrkraft-a", "remote-email": "a@example.org", "remote-sub": "sub-a"}
KOPF_B = {"remote-user": "lehrkraft-b", "remote-email": "b@example.org", "remote-sub": "sub-b"}

KENNUNG_IM_HTML = re.compile(r"/ablage/([0-9a-f-]{36})/oeffnen")


def quiz_json(titel: str = "Probequiz", fragen: int = 2, bild_bytes: int = 0) -> str:
    slides = []
    for nummer in range(fragen):
        media = None
        if bild_bytes:
            media = {"Image": {"Base64": {"data": "data:image/png;base64," + "A" * bild_bytes,
                                          "alt": "Probe"}}}
        slides.append({"InfoSlide": {"title": f"Folie {nummer + 1}", "body": "Text",
                                     "media": media, "duration": None}})
    return json.dumps({"title": titel, "slides": slides}, ensure_ascii=False)


def quiz_ids(seite: str) -> list[str]:
    return KENNUNG_IM_HTML.findall(seite)


def einzige_kennung(seite: str) -> str:
    kennungen = quiz_ids(seite)
    assert kennungen, "keine Quiz-Kennung auf der Seite gefunden"
    return kennungen[0]


@pytest.fixture()
def umgebung(tmp_path, monkeypatch):
    ablage = tmp_path / "ablage.db"
    kv = tmp_path / "kv.db"
    with sqlite3.connect(kv) as v:
        v.execute("CREATE TABLE kv_share (key TEXT PRIMARY KEY, value TEXT NOT NULL, "
                  "expires_at INTEGER)")

    monkeypatch.setenv("FUIZSTASH_DATEN", str(ablage))
    monkeypatch.setenv("FUIZ_KV", str(kv))

    from app import main

    with TestClient(main.app) as klient:
        yield {
            "klient": klient,
            "kv_pfad": kv,
            "ablage_pfad": ablage,
            "teilen": lambda wert, frist=None: _teilen(kv, wert, frist),
            "kv_zeilen": lambda: _zeilen(kv),
        }


def _teilen(kv, wert: str, frist=None) -> str:
    kennung = str(uuid.uuid4())
    with sqlite3.connect(kv) as v:
        v.execute("INSERT INTO kv_share (key, value, expires_at) VALUES (?, ?, ?)",
                  (kennung, wert, frist))
    return kennung


def _zeilen(kv):
    with sqlite3.connect(kv) as v:
        return v.execute("SELECT key, value, expires_at FROM kv_share ORDER BY key").fetchall()


def einreichen(umgebung, eingabe: str, kopf=KOPF_A, folgen=True):
    return umgebung["klient"].post("/ablage/einreichen", data={"eingabe": eingabe},
                                   headers=kopf, follow_redirects=folgen)


# ---------------------------------------------------------------- Zugang

def test_ohne_kopfzeilen_kein_zugriff(umgebung):
    antwort = umgebung["klient"].get("/ablage")
    assert antwort.status_code == 401
    assert "Anmeldung" in antwort.json()["detail"]


def test_gesundheit_meldet_kopplung(umgebung):
    daten = umgebung["klient"].get("/gesundheit").json()
    assert daten["ok"] is True
    assert daten["teilen_speicher"]["tabelle_ok"] is True
    assert daten["teilen_speicher"]["schreibbar"] is True


def test_fremde_herkunft_abgelehnt(umgebung):
    antwort = umgebung["klient"].post(
        "/ablage/einreichen", data={"eingabe": str(uuid.uuid4())},
        headers=KOPF_A | {"origin": "https://boese.example"}, follow_redirects=False,
    )
    assert antwort.status_code == 403


def test_eigene_herkunft_erlaubt(umgebung):
    kennung = umgebung["teilen"](quiz_json("Erlaubt"))
    antwort = umgebung["klient"].post(
        "/ablage/einreichen", data={"eingabe": kennung},
        headers=KOPF_A | {"origin": "http://testserver"}, follow_redirects=False,
    )
    assert antwort.status_code == 303


# ---------------------------------------------------------------- Einreichen

def test_einreichen_mit_bild(umgebung):
    kennung = umgebung["teilen"](quiz_json("Mit Bild", fragen=3, bild_bytes=400))
    antwort = einreichen(umgebung, kennung)
    assert antwort.status_code == 200
    assert "Mit Bild" in antwort.text
    assert "3 Fragen" in antwort.text
    assert "liegt jetzt in Ihrer Ablage" in antwort.text


def test_einreichen_akzeptiert_vollen_link(umgebung):
    kennung = umgebung["teilen"](quiz_json("Linkform"))
    antwort = einreichen(umgebung, f"https://fuiz.mekotools.de/share/{kennung}")
    assert "Linkform" in antwort.text


def test_fremder_anbieter_abgelehnt(umgebung):
    antwort = einreichen(umgebung, f"https://fuiz.org/share/{uuid.uuid4()}")
    assert "nicht zu unserer fuiz-Instanz" in antwort.text
    assert "Noch keine Quizze abgelegt" in antwort.text


def test_kennung_mit_falscher_form_wird_nicht_nachgeschlagen(umgebung):
    """Form zuerst prüfen: eine kaputte Kennung darf nie im Speicher landen."""
    antwort = einreichen(umgebung, "abc-123")
    assert "Teilen-Kennung" in antwort.text
    assert "Noch keine Quizze abgelegt" in antwort.text
    assert not umgebung["kv_zeilen"]() is None  # Speicher unangetastet: nur Lesen
    assert len(umgebung["kv_zeilen"]()) == 0


def test_unbekannte_kennung_ohne_eintrag(umgebung):
    antwort = einreichen(umgebung, str(uuid.uuid4()))
    assert "kennt fuiz nicht (mehr)" in antwort.text
    assert "Noch keine Quizze abgelegt" in antwort.text


def test_abgelaufene_kennung_ohne_eintrag(umgebung):
    kennung = umgebung["teilen"](quiz_json("Alt"), frist=1)
    antwort = einreichen(umgebung, kennung)
    assert "kennt fuiz nicht (mehr)" in antwort.text


def test_unlesbarer_inhalt_wird_gemeldet(umgebung):
    kennung = umgebung["teilen"]("kein json")
    antwort = einreichen(umgebung, kennung)
    assert "ließ sich nicht lesen" in antwort.text


def test_kein_titel_wird_gemeldet(umgebung):
    kennung = umgebung["teilen"](json.dumps({"slides": []}))
    antwort = einreichen(umgebung, kennung)
    assert "fehlt der Titel" in antwort.text


# ---------------------------------------------------------------- Trennung

def test_zwei_nutzer_sehen_getrennte_bestaende(umgebung):
    kennung = umgebung["teilen"](quiz_json("Geheim von A"))
    einreichen(umgebung, kennung)

    seite_a = umgebung["klient"].get("/ablage", headers=KOPF_A).text
    quiz_id = einzige_kennung(seite_a)

    seite_b = umgebung["klient"].get("/ablage", headers=KOPF_B).text
    assert "Geheim von A" not in seite_b
    assert "Noch keine Quizze abgelegt" in seite_b

    # B darf den Eintrag von A weder öffnen noch löschen
    oeffnen = umgebung["klient"].get(f"/ablage/{quiz_id}/oeffnen", headers=KOPF_B)
    assert "nicht (mehr) vorhanden" in oeffnen.text
    loeschen = umgebung["klient"].post(f"/ablage/{quiz_id}/loeschen", headers=KOPF_B)
    assert "nicht gefunden" in loeschen.text
    assert "Geheim von A" in umgebung["klient"].get("/ablage", headers=KOPF_A).text


# ---------------------------------------------------------------- Übernahme

def test_uebernahme_legt_dauerhaften_eintrag_an(umgebung):
    inhalt = quiz_json("Zum Öffnen", fragen=1)
    einreichen(umgebung, umgebung["teilen"](inhalt))
    quiz_id = einzige_kennung(umgebung["klient"].get("/ablage", headers=KOPF_A).text)

    antwort = umgebung["klient"].get(f"/ablage/{quiz_id}/oeffnen", headers=KOPF_A,
                                     follow_redirects=False)
    assert antwort.status_code == 303
    ziel = antwort.headers["location"]
    assert ziel.startswith("https://fuiz.mekotools.de/share/")
    uebernahme = ziel.rsplit("/", 1)[1]

    zeilen = {z[0]: z for z in umgebung["kv_zeilen"]()}
    assert uebernahme in zeilen
    assert zeilen[uebernahme][2] is None          # ohne Frist = dauerhaft
    assert json.loads(zeilen[uebernahme][1])["title"] == "Zum Öffnen"


def test_uebernahmekennung_ueberlebt_aufraeumen(umgebung):
    einreichen(umgebung, umgebung["teilen"](quiz_json("Bleibt")))
    quiz_id = einzige_kennung(umgebung["klient"].get("/ablage", headers=KOPF_A).text)
    erste = umgebung["klient"].get(f"/ablage/{quiz_id}/oeffnen", headers=KOPF_A,
                                   follow_redirects=False).headers["location"].rsplit("/", 1)[1]

    # fuiz' eigener Aufräumlauf entfernt nur abgelaufene Zeilen
    with sqlite3.connect(umgebung["kv_pfad"]) as v:
        v.execute("DELETE FROM kv_share WHERE expires_at IS NOT NULL AND expires_at <= 99999999999")

    zweite = umgebung["klient"].get(f"/ablage/{quiz_id}/oeffnen", headers=KOPF_A,
                                    follow_redirects=False).headers["location"].rsplit("/", 1)[1]
    assert zweite == erste


def test_neueinreichung_ersetzt_und_aktualisiert_uebernahmelink(umgebung):
    einreichen(umgebung, umgebung["teilen"](quiz_json("Wandelt sich", fragen=1)))
    quiz_id = einzige_kennung(umgebung["klient"].get("/ablage", headers=KOPF_A).text)
    uebernahme = umgebung["klient"].get(f"/ablage/{quiz_id}/oeffnen", headers=KOPF_A,
                                        follow_redirects=False).headers["location"].rsplit("/", 1)[1]

    antwort = einreichen(umgebung, umgebung["teilen"](quiz_json("Wandelt sich", fragen=4)))
    assert "wurde aktualisiert" in antwort.text

    seite = antwort.text
    assert "4 Fragen" in seite
    assert "1× neu eingereicht" in seite
    assert seite.count("<h3>Wandelt sich</h3>") == 1
    assert einzige_kennung(seite) == quiz_id
    zeilen = {z[0]: z for z in umgebung["kv_zeilen"]()}
    assert len(json.loads(zeilen[uebernahme][1])["slides"]) == 4


def test_gleichnamiges_quiz_einer_anderen_person_bleibt_getrennt(umgebung):
    einreichen(umgebung, umgebung["teilen"](quiz_json("Doppelt", fragen=2)))
    einreichen(umgebung, umgebung["teilen"](quiz_json("Doppelt", fragen=5)), kopf=KOPF_B)
    seite_a = umgebung["klient"].get("/ablage", headers=KOPF_A).text
    seite_b = umgebung["klient"].get("/ablage", headers=KOPF_B).text
    assert "2 Fragen" in seite_a and "5 Fragen" not in seite_a
    assert "5 Fragen" in seite_b and "2 Fragen" not in seite_b
    assert einzige_kennung(seite_a) != einzige_kennung(seite_b)


# ---------------------------------------------------------------- Löschen

def test_papierkorb_und_wiederherstellen(umgebung):
    einreichen(umgebung, umgebung["teilen"](quiz_json("Weg und zurück")))
    quiz_id = einzige_kennung(umgebung["klient"].get("/ablage", headers=KOPF_A).text)

    antwort = umgebung["klient"].post(f"/ablage/{quiz_id}/loeschen", headers=KOPF_A)
    assert "liegt im Papierkorb" in antwort.text
    assert "Weg und zurück" in antwort.text          # steht noch im Papierkorb
    assert "Noch keine Quizze abgelegt" in antwort.text

    zurueck = umgebung["klient"].post(f"/ablage/{quiz_id}/wiederherstellen", headers=KOPF_A)
    assert "ist wieder da" in zurueck.text
    assert "Papierkorb" not in zurueck.text.split("Ihre Quizze")[0]


def test_endgueltig_loeschen_laesst_nichts_zurueck(umgebung):
    einreichen(umgebung, umgebung["teilen"](quiz_json("Ganz weg")))
    quiz_id = einzige_kennung(umgebung["klient"].get("/ablage", headers=KOPF_A).text)
    uebernahme = umgebung["klient"].get(f"/ablage/{quiz_id}/oeffnen", headers=KOPF_A,
                                        follow_redirects=False).headers["location"].rsplit("/", 1)[1]

    umgebung["klient"].post(f"/ablage/{quiz_id}/loeschen", headers=KOPF_A)
    antwort = umgebung["klient"].post(f"/ablage/{quiz_id}/endgueltig", headers=KOPF_A)
    assert "endgültig gelöscht" in antwort.text
    assert "Weg" not in antwort.text

    zeilen = {z[0]: z for z in umgebung["kv_zeilen"]()}
    assert uebernahme not in zeilen
    with sqlite3.connect(umgebung["ablage_pfad"]) as v:
        assert v.execute("SELECT COUNT(*) FROM quiz").fetchone()[0] == 0
        assert v.execute("SELECT COUNT(*) FROM ereignis WHERE quiz_id = ?", (quiz_id,)).fetchone()[0] == 0


def test_papierkorb_raeumt_nach_ablauf(umgebung):
    einreichen(umgebung, umgebung["teilen"](quiz_json("Fristablauf")))
    quiz_id = einzige_kennung(umgebung["klient"].get("/ablage", headers=KOPF_A).text)
    umgebung["klient"].post(f"/ablage/{quiz_id}/loeschen", headers=KOPF_A)

    with sqlite3.connect(umgebung["ablage_pfad"]) as v:
        v.execute("UPDATE quiz SET geloescht_am = '2000-01-01T00:00:00+00:00'")

    from app import datenbank

    assert datenbank.papierkorb_raeumen() == 1
    with sqlite3.connect(umgebung["ablage_pfad"]) as v:
        assert v.execute("SELECT COUNT(*) FROM quiz").fetchone()[0] == 0


# ---------------------------------------------------------------- Grenzen

def test_grenze_je_quiz_wird_vorher_gemeldet(umgebung):
    umgebung["klient"].post("/einstellungen", headers=KOPF_A,
                            data={"max_quiz_mb": "1", "max_nutzer_mb": "50",
                                  "papierkorb_tage": "30"})
    kennung = umgebung["teilen"](quiz_json("Zu groß", fragen=1, bild_bytes=1_400_000))
    antwort = einreichen(umgebung, kennung)
    assert "über der Grenze" in antwort.text
    assert "Noch keine Quizze abgelegt" in antwort.text


def test_grenze_je_nutzer_wird_vorher_gemeldet(umgebung):
    umgebung["klient"].post("/einstellungen", headers=KOPF_A,
                            data={"max_quiz_mb": "10", "max_nutzer_mb": "10",
                                  "papierkorb_tage": "30"})
    einreichen(umgebung, umgebung["teilen"](quiz_json("Voll 1", fragen=1, bild_bytes=7_000_000)))
    antwort = einreichen(umgebung, umgebung["teilen"](quiz_json("Voll 2", fragen=1,
                                                               bild_bytes=7_000_000)))
    assert "Speicher ist voll" in antwort.text
    assert "Voll 1" in antwort.text and "Voll 2" not in antwort.text


def test_ersetzung_zaehlt_nicht_doppelt_gegen_die_grenze(umgebung):
    umgebung["klient"].post("/einstellungen", headers=KOPF_A,
                            data={"max_quiz_mb": "10", "max_nutzer_mb": "3",
                                  "papierkorb_tage": "30"})
    einreichen(umgebung, umgebung["teilen"](quiz_json("Groß", fragen=1, bild_bytes=1_400_000)))
    antwort = einreichen(umgebung, umgebung["teilen"](quiz_json("Groß", fragen=1,
                                                               bild_bytes=1_400_000)))
    assert "wurde aktualisiert" in antwort.text


def test_einstellungen_lehnen_unsinn_ab(umgebung):
    antwort = umgebung["klient"].post("/einstellungen", headers=KOPF_A,
                                      data={"max_quiz_mb": "0", "max_nutzer_mb": "99999",
                                            "papierkorb_tage": "x"})
    assert "Nicht gespeichert" in antwort.text
    assert 'value="25"' in antwort.text  # Vorgabe unverändert


# ---------------------------------------------------------------- Kopplung

def test_fehlende_kopplung_wird_sichtbar_gemeldet(umgebung, monkeypatch):
    monkeypatch.setenv("FUIZ_KV", "/gibt-es-nicht/kv.db")
    seite = umgebung["klient"].get("/ablage", headers=KOPF_A).text
    assert "Verbindung zu fuiz gestört" in seite
    assert umgebung["klient"].get("/gesundheit").json()["ok"] is False

    antwort = einreichen(umgebung, str(uuid.uuid4()))
    assert "nicht erreichbar" in antwort.text


def test_fehlende_tabelle_wird_gemeldet(umgebung, tmp_path, monkeypatch):
    leer = tmp_path / "leer.db"
    with sqlite3.connect(leer) as v:
        v.execute("CREATE TABLE etwas_anderes (x TEXT)")
    monkeypatch.setenv("FUIZ_KV", str(leer))
    daten = umgebung["klient"].get("/gesundheit").json()
    assert daten["ok"] is False
    assert "kv_share fehlt" in daten["teilen_speicher"]["hinweis"]
