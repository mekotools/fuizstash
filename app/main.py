"""MekoTools-Quizablage — Ablage für fuiz-Quizze, an der Anmeldung hängend.

Zugang ausschließlich über die Sperre (Forward-Auth): die Identität kommt aus
den Kopfzeilen `remote-user`, `remote-email`, `remote-sub`. Ohne diese
Kopfzeilen gibt es keine Inhalte und keine Handlungen.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import datenbank, fuizspeicher, kennungen

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
protokoll = logging.getLogger("quizablage")

BASISORDNER = os.path.dirname(__file__)
FUIZ_BASIS = os.environ.get("ABLAGE_FUIZ_BASIS", "https://fuiz.mekotools.de").rstrip("/")
AUFBEWAHRUNG_STUNDEN = int(os.environ.get("ABLAGE_RAEUMEN_STUNDEN", "6"))


@dataclass
class Nutzer:
    schluessel: str
    anzeige: str
    mail: str | None


def _raeumen_im_hintergrund() -> asyncio.Task:
    async def schleife() -> None:
        while True:
            try:
                entfernt = await asyncio.to_thread(datenbank.papierkorb_raeumen)
                if entfernt:
                    protokoll.info("Papierkorb: %s Einträge endgültig entfernt", entfernt)
            except Exception:  # noqa: BLE001 - Hintergrundlauf darf nie sterben
                protokoll.exception("Papierkorb-Räumung fehlgeschlagen")
            await asyncio.sleep(AUFBEWAHRUNG_STUNDEN * 3600)

    return asyncio.create_task(schleife())


@asynccontextmanager
async def lebensdauer(app: FastAPI):
    datenbank.einrichten()
    lage = fuizspeicher.kopplung_pruefen()
    if lage.gesund:
        protokoll.info("Kopplung an fuiz bereit: %s", lage.pfad)
    else:
        protokoll.error("Kopplung an fuiz NICHT bereit: %s", lage.hinweis)
    aufgabe = _raeumen_im_hintergrund()
    yield
    aufgabe.cancel()


app = FastAPI(title="MekoTools-Quizablage", lifespan=lebensdauer, docs_url=None, redoc_url=None)
app.mount("/statisch", StaticFiles(directory=os.path.join(BASISORDNER, "statisch")), name="statisch")
vorlagen = Jinja2Templates(directory=os.path.join(BASISORDNER, "vorlagen"))


# ---------------------------------------------------------------- Zugang

def nutzer_lesen(request: Request) -> Nutzer:
    kopf = request.headers
    kennung = (kopf.get("remote-sub") or "").strip()
    benutzer = (kopf.get("remote-user") or "").strip()
    mail = (kopf.get("remote-email") or "").strip() or None
    name = (kopf.get("remote-name") or "").strip()
    schluessel = kennung or mail or benutzer
    if not schluessel:
        protokoll.warning(
            "Aufruf ohne Kopfzeilen der Sperre: %s %s", request.method, request.url.path
        )
        raise HTTPException(
            status_code=401,
            detail="Keine Anmeldung erkennbar. Dieser Dienst ist nur über die MekoTools-Anmeldung erreichbar.",
        )
    return Nutzer(schluessel=schluessel.lower(), anzeige=name or benutzer or mail or schluessel, mail=mail)


def herkunft_pruefen(request: Request) -> None:
    """Einfacher Herkunftsschutz für schreibende Aufrufe (Formulare derselben Seite)."""
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    herkunft = request.headers.get("origin") or request.headers.get("referer")
    if not herkunft:
        return
    eigene = {str(request.base_url).rstrip("/")}
    weitergeleitet = (request.headers.get("x-forwarded-host") or "").strip().lower()
    if weitergeleitet:
        eigene.add(f"https://{weitergeleitet}")
        eigene.add(f"http://{weitergeleitet}")
    if not any(herkunft.startswith(e) for e in eigene):
        raise HTTPException(status_code=403, detail="Aufruf von fremder Herkunft abgelehnt.")


@app.middleware("http")
async def herkunft_middleware(request: Request, aufruf):
    try:
        herkunft_pruefen(request)
    except HTTPException as fehler:
        # Fehler aus der Middleware erreichen die Ausnahmebehandlung der App nicht —
        # deshalb hier ausdrücklich als Antwort zurückgeben.
        return JSONResponse({"detail": fehler.detail}, status_code=fehler.status_code)
    return await aufruf(request)


# ---------------------------------------------------------------- Hilfen

def groesse_text(byte: int) -> str:
    if byte < 1024:
        return f"{byte} B"
    if byte < 1024 * 1024:
        return f"{byte / 1024:.0f} KB"
    return f"{byte / (1024 * 1024):.1f} MB"


def zeit_text(wert: str | None) -> str:
    if not wert:
        return "—"
    try:
        zeit = datetime.fromisoformat(wert)
    except ValueError:
        return wert
    return zeit.astimezone().strftime("%d.%m.%Y, %H:%M")


def grenzen() -> dict[str, float]:
    werte = datenbank.einstellungen()
    return {
        "quiz": float(werte["max_quiz_mb"]) * 1024 * 1024,
        "nutzer": float(werte["max_nutzer_mb"]) * 1024 * 1024,
        "quiz_mb": float(werte["max_quiz_mb"]),
        "nutzer_mb": float(werte["max_nutzer_mb"]),
        "tage": int(werte["papierkorb_tage"]),
    }


_kopplung_cache: dict[str, object] = {"zeit": 0.0, "lage": None, "pfad": ""}


def kopplung_aktuell(sekunden: int = 30):
    """Die Kopplung wird höchstens alle `sekunden` Sekunden geprüft — die Prüfung
    schreibt einen Probeeintrag und soll nicht bei jedem Seitenaufbau laufen.
    Ein anderer Pfad erzwingt sofort eine neue Prüfung."""
    jetzt = time.monotonic()
    aktueller_pfad = fuizspeicher.pfad()
    veraltet = (
        _kopplung_cache["lage"] is None
        or _kopplung_cache["pfad"] != aktueller_pfad
        or jetzt - float(_kopplung_cache["zeit"]) > sekunden
    )
    if veraltet:
        _kopplung_cache["lage"] = fuizspeicher.kopplung_pruefen()
        _kopplung_cache["zeit"] = jetzt
        _kopplung_cache["pfad"] = aktueller_pfad
    return _kopplung_cache["lage"]


def seite(request: Request, name: str, nutzer: Nutzer, **werte) -> HTMLResponse:
    lage = kopplung_aktuell()
    gemeinsam = {
        "request": request,
        "nutzer": nutzer,
        "kopplung": lage,
        "fuiz_basis": FUIZ_BASIS,
        "meldung": request.query_params.get("meldung"),
        "art": request.query_params.get("art", "gut"),
    }
    gemeinsam.update(werte)
    return vorlagen.TemplateResponse(request, name, gemeinsam)


def weiter(ziel: str, meldung: str, art: str = "gut") -> RedirectResponse:
    trenner = "&" if "?" in ziel else "?"
    from urllib.parse import quote

    return RedirectResponse(
        f"{ziel}{trenner}meldung={quote(meldung)}&art={art}", status_code=303
    )


# ---------------------------------------------------------------- Seiten

@app.get("/", include_in_schema=False)
async def wurzel() -> RedirectResponse:
    return RedirectResponse("/ablage", status_code=307)


@app.get("/gesundheit", include_in_schema=False)
async def gesundheit() -> JSONResponse:
    lage = fuizspeicher.kopplung_pruefen()
    return JSONResponse(
        {
            "ok": lage.gesund,
            "teilen_speicher": {
                "pfad": lage.pfad,
                "vorhanden": lage.vorhanden,
                "tabelle_ok": lage.tabelle_ok,
                "schreibbar": lage.schreibbar,
                "hinweis": lage.hinweis,
            },
            "datenbank": datenbank.pfad(),
        }
    )


@app.get("/ablage", response_class=HTMLResponse)
async def ablage(request: Request, nutzer: Nutzer = Depends(nutzer_lesen)) -> HTMLResponse:
    eintraege = datenbank.liste(nutzer.schluessel)
    papierkorb = datenbank.liste(nutzer.schluessel, papierkorb=True)
    grenze = grenzen()
    belegt = datenbank.belegung(nutzer.schluessel)
    return seite(
        request,
        "ablage.html",
        nutzer,
        eintraege=eintraege,
        papierkorb=papierkorb,
        ereignisse=datenbank.ereignisse(nutzer.schluessel, 8),
        belegt=belegt,
        belegt_text=groesse_text(belegt),
        grenze=grenze,
        anteil=min(100, round(belegt / grenze["nutzer"] * 100)) if grenze["nutzer"] else 0,
        groesse_text=groesse_text,
        zeit_text=zeit_text,
    )


@app.post("/ablage/einreichen")
async def einreichen(
    request: Request,
    eingabe: str = Form(...),
    nutzer: Nutzer = Depends(nutzer_lesen),
) -> RedirectResponse:
    grenze = grenzen()
    try:
        kennung = kennungen.kennung_lesen(eingabe)
    except kennungen.KennungFehler as fehler:
        datenbank.ereignis("einreichen", f"abgelehnt: {fehler}", nutzer.schluessel)
        return weiter("/ablage", str(fehler), "fehler")

    try:
        roh = fuizspeicher.inhalt_holen(kennung)
    except fuizspeicher.SpeicherFehler as fehler:
        datenbank.ereignis("einreichen", f"Speicherfehler: {fehler}", nutzer.schluessel)
        return weiter("/ablage", f"Der Teilen-Speicher ist nicht erreichbar: {fehler}", "fehler")

    if roh is None:
        datenbank.ereignis("einreichen", f"unbekannt/abgelaufen: {kennung}", nutzer.schluessel)
        return weiter(
            "/ablage",
            "Diese Kennung kennt fuiz nicht (mehr). Teilen-Links laufen nach 30 Tagen ab — "
            "bitte in fuiz erneut teilen und den neuen Link einfügen.",
            "fehler",
        )

    try:
        inhalt = fuizspeicher.pruefe_inhalt(roh)
    except fuizspeicher.SpeicherFehler as fehler:
        datenbank.ereignis("einreichen", f"unlesbar: {fehler}", nutzer.schluessel)
        return weiter("/ablage", f"Der Inhalt ließ sich nicht lesen: {fehler}", "fehler")

    groesse = len(roh.encode())
    if groesse > grenze["quiz"]:
        return weiter(
            "/ablage",
            f"Dieses Quiz ist {groesse_text(groesse)} groß und liegt über der Grenze von "
            f"{grenze['quiz_mb']:.0f} MB je Quiz.",
            "fehler",
        )

    titel = inhalt["title"].strip()
    fragen = len(inhalt["slides"])
    bisher = datenbank.nach_titel(nutzer.schluessel, titel)
    zusatz = 0 if bisher else groesse
    if datenbank.belegung(nutzer.schluessel) + zusatz > grenze["nutzer"]:
        return weiter(
            "/ablage",
            f"Der Speicher ist voll: {groesse_text(datenbank.belegung(nutzer.schluessel))} von "
            f"{grenze['nutzer_mb']:.0f} MB belegt. Bitte zuerst etwas löschen.",
            "fehler",
        )

    if bisher:
        datenbank.ersetzen(nutzer.schluessel, bisher.id, fragen, roh, kennung)
        if bisher.uebernahme_kennung:
            # Ein bereits geteilter Übernahme-Link zeigt danach den neuen Stand.
            try:
                fuizspeicher.uebernahme_eintragen(roh, bisher.uebernahme_kennung)
            except fuizspeicher.SpeicherFehler as fehler:
                protokoll.warning("Übernahme-Eintrag nicht aktualisiert: %s", fehler)
        datenbank.ereignis(
            "ersetzen",
            f"„{titel}“ neu eingereicht ({fragen} Fragen, {groesse_text(groesse)})",
            nutzer.schluessel,
            bisher.id,
        )
        return weiter("/ablage", f"„{titel}“ wurde aktualisiert ({fragen} Fragen).")

    kennung_neu = datenbank.anlegen(
        nutzer.schluessel, nutzer.mail, titel, fragen, roh, "teilen", kennung
    )
    datenbank.ereignis(
        "einreichen",
        f"„{titel}“ abgelegt ({fragen} Fragen, {groesse_text(groesse)})",
        nutzer.schluessel,
        kennung_neu,
    )
    return weiter("/ablage", f"„{titel}“ liegt jetzt in Ihrer Ablage ({fragen} Fragen).")


@app.get("/ablage/{quiz_id}/oeffnen")
async def oeffnen(quiz_id: str, nutzer: Nutzer = Depends(nutzer_lesen)) -> RedirectResponse:
    eintrag = datenbank.holen(nutzer.schluessel, quiz_id)
    if not eintrag or eintrag.im_papierkorb:
        return weiter("/ablage", "Dieser Eintrag ist nicht (mehr) vorhanden.", "fehler")
    try:
        kennung = eintrag.uebernahme_kennung
        if not kennung or not fuizspeicher.uebernahme_vorhanden(kennung):
            kennung = fuizspeicher.uebernahme_eintragen(eintrag.inhalt, kennung)
            datenbank.uebernahme_setzen(nutzer.schluessel, eintrag.id, kennung)
        datenbank.ereignis("oeffnen", f"„{eintrag.titel}“ in fuiz geöffnet", nutzer.schluessel, eintrag.id)
    except fuizspeicher.SpeicherFehler as fehler:
        datenbank.ereignis("oeffnen", f"fehlgeschlagen: {fehler}", nutzer.schluessel, eintrag.id)
        return weiter("/ablage", f"Übernahme nicht möglich: {fehler}", "fehler")
    return RedirectResponse(f"{FUIZ_BASIS}/share/{kennung}", status_code=303)


@app.get("/ablage/{quiz_id}/sicherung")
async def sicherung(quiz_id: str, nutzer: Nutzer = Depends(nutzer_lesen)) -> PlainTextResponse:
    eintrag = datenbank.holen(nutzer.schluessel, quiz_id)
    if not eintrag:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden.")
    name = "".join(c for c in eintrag.titel if c.isalnum() or c in " -_").strip() or "quiz"
    return PlainTextResponse(
        eintrag.inhalt,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}.fuiz.json"'},
    )


@app.post("/ablage/{quiz_id}/loeschen")
async def loeschen(quiz_id: str, nutzer: Nutzer = Depends(nutzer_lesen)) -> RedirectResponse:
    eintrag = datenbank.holen(nutzer.schluessel, quiz_id, mit_inhalt=False)
    if not eintrag:
        return weiter("/ablage", "Eintrag nicht gefunden.", "fehler")
    datenbank.loeschen(nutzer.schluessel, quiz_id)
    datenbank.ereignis("loeschen", f"„{eintrag.titel}“ in den Papierkorb", nutzer.schluessel, quiz_id)
    return weiter("/ablage", f"„{eintrag.titel}“ liegt im Papierkorb ({grenzen()['tage']} Tage).")


@app.post("/ablage/{quiz_id}/wiederherstellen")
async def wiederherstellen(quiz_id: str, nutzer: Nutzer = Depends(nutzer_lesen)) -> RedirectResponse:
    eintrag = datenbank.holen(nutzer.schluessel, quiz_id, mit_inhalt=False)
    if not eintrag:
        return weiter("/ablage", "Eintrag nicht gefunden.", "fehler")
    datenbank.wiederherstellen(nutzer.schluessel, quiz_id)
    datenbank.ereignis("wiederherstellen", f"„{eintrag.titel}“ wiederhergestellt", nutzer.schluessel, quiz_id)
    return weiter("/ablage", f"„{eintrag.titel}“ ist wieder da.")


@app.post("/ablage/{quiz_id}/endgueltig")
async def endgueltig(quiz_id: str, nutzer: Nutzer = Depends(nutzer_lesen)) -> RedirectResponse:
    eintrag = datenbank.holen(nutzer.schluessel, quiz_id)
    if not eintrag:
        return weiter("/ablage", "Eintrag nicht gefunden.", "fehler")
    entfernt = False
    if eintrag.uebernahme_kennung:
        entfernt = datenbank.uebernahme_entfernen(eintrag.uebernahme_kennung)
    datenbank.endgueltig_loeschen(nutzer.schluessel, quiz_id)
    datenbank.verdichten()
    datenbank.ereignis(
        "endgueltig",
        f"„{eintrag.titel}“ endgültig gelöscht"
        + (" (Übernahme-Link entfernt)" if entfernt else " (kein Übernahme-Link vorhanden)"),
        nutzer.schluessel,
    )
    return weiter("/ablage", f"„{eintrag.titel}“ ist endgültig gelöscht.")


@app.get("/einstellungen", response_class=HTMLResponse)
async def einstellungen_seite(request: Request, nutzer: Nutzer = Depends(nutzer_lesen)) -> HTMLResponse:
    return seite(
        request,
        "einstellungen.html",
        nutzer,
        werte=datenbank.einstellungen(),
        beschreibung=datenbank.BESCHREIBUNG,
    )


@app.post("/einstellungen")
async def einstellungen_speichern(
    max_quiz_mb: str = Form(...),
    max_nutzer_mb: str = Form(...),
    papierkorb_tage: str = Form(...),
    nutzer: Nutzer = Depends(nutzer_lesen),
) -> RedirectResponse:
    geprueft: dict[str, str] = {}
    fehler: list[str] = []
    schranken = {"max_quiz_mb": (1, 500), "max_nutzer_mb": (10, 5000), "papierkorb_tage": (1, 365)}
    for schluessel, wert in (
        ("max_quiz_mb", max_quiz_mb),
        ("max_nutzer_mb", max_nutzer_mb),
        ("papierkorb_tage", papierkorb_tage),
    ):
        try:
            zahl = int(float(wert.replace(",", ".")))
        except ValueError:
            fehler.append(f"{schluessel}: keine Zahl")
            continue
        unten, oben = schranken[schluessel]
        if not unten <= zahl <= oben:
            fehler.append(f"{schluessel}: erlaubt {unten} bis {oben}")
            continue
        geprueft[schluessel] = str(zahl)

    if fehler:
        return weiter("/einstellungen", "Nicht gespeichert — " + "; ".join(fehler), "fehler")
    geaendert = datenbank.einstellungen_setzen(geprueft)
    datenbank.ereignis("einstellungen", "geändert: " + ", ".join(geaendert), nutzer.schluessel)
    return weiter("/einstellungen", "Gespeichert: " + ", ".join(geaendert))


@app.get("/verlauf", response_class=HTMLResponse)
async def verlauf(request: Request, nutzer: Nutzer = Depends(nutzer_lesen)) -> HTMLResponse:
    return seite(
        request,
        "verlauf.html",
        nutzer,
        ereignisse=datenbank.ereignisse(nutzer.schluessel, 200),
        zeit_text=zeit_text,
    )
