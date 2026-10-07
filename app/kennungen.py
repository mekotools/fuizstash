"""Kennungen von fuiz lesen und prüfen.

Zwei Formen sind erlaubt: die reine Kennung (UUID, wie sie beim Teilen entsteht)
und der vollständige Link unserer fuiz-Instanz. Eine fremde Adresse (z. B.
fuiz.org) wird ausdrücklich abgelehnt, weil deren Inhalt nicht in unserem
Teilen-Speicher liegt.
"""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse

# Genau die Form, die fuiz beim Teilen erzeugt (crypto.randomUUID → Version 4).
KENNUNG_MUSTER = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class KennungFehler(ValueError):
    """Die Eingabe ist keine brauchbare Kennung — mit Klartextgrund."""


def erlaubte_hosts() -> set[str]:
    roh = os.environ.get("FUIZSTASH_FUIZ_HOSTS", "fuiz.mekotools.de,fuiz.app.n0ne.de")
    return {h.strip().lower() for h in roh.split(",") if h.strip()}


def kennung_lesen(eingabe: str) -> str:
    """Zieht die Kennung aus Link oder reiner Kennung.

    Reihenfolge ist Absicht: erst die Form prüfen, dann verwenden. Eine
    Kennung, die die Form verletzt, wird nie nachgeschlagen.
    """
    text = (eingabe or "").strip()
    if not text:
        raise KennungFehler("Bitte einen Teilen-Link oder eine Kennung angeben.")

    if text.startswith("http://") or text.startswith("https://"):
        teile = urlparse(text)
        host = (teile.hostname or "").lower()
        if host not in erlaubte_hosts():
            raise KennungFehler(
                "Dieser Link gehört nicht zu unserer fuiz-Instanz. Teilen-Links "
                "anderer Anbieter lassen sich hier nicht ablegen."
            )
        pfad = teile.path.rstrip("/")
        treffer = re.search(r"/share/([^/?#]+)$", pfad)
        if not treffer:
            raise KennungFehler(
                "Dem Link fehlt der Teil „/share/<Kennung>“. Bitte in fuiz auf "
                "„Teilen“ gehen und den ganzen Link einfügen."
            )
        text = treffer.group(1)

    if not KENNUNG_MUSTER.match(text):
        raise KennungFehler(
            "Das sieht nicht nach einer Teilen-Kennung aus (erwartet: "
            "8-4-4-4-12 Zeichen, z. B. 4f4a1d92-6f3b-4a1e-9d2c-0b1f5e6a7c88)."
        )
    return text.lower()
