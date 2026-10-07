/* MekoTools-Zusatz für fuiz — „In Fuizstash ablegen" neben dem Teilen-Eintrag.
 *
 * Wird vom Schieber vor fuiz eingehängt (Stapel mekotools-fuiz-zusatz); die
 * digest-genagelten fuiz-Abbilder bleiben unangetastet.
 *
 * Warum dieser Weg: fuiz zeigt den Teilen-Link nirgends an — es legt ihn über
 * navigator.clipboard.writeText in die Zwischenablage und blendet „Kopiert!" ein.
 * Deshalb liest dieses Skript die Zwischenablage-Abgabe mit (Punkt 1), zeigt danach
 * selbst einen Ablege-Link (Punkt 2) und kann den Teilen-Eintrag im Optionen-Menü
 * selbst auslösen, wenn man den Zusatzeintrag anklickt (Punkt 3).
 */
(() => {
  'use strict';

  const ZIEL = 'https://fuizstash.mekotools.de/ablage';
  const MUSTER = /\/share\/[0-9a-f][0-9a-f-]{7,}/i; // nur fuiz-Teilungsadressen
  const MARKE = 'data-mekotools-zusatz';
  const WARTEZEIT = 8000;

  // Beschriftungen des Teilen-Eintrags in allen Sprachen, die fuiz mitbringt:
  // daran wird der Anker erkannt, ohne sich auf Klassennamen zu verlassen.
  const TEILEN = ['Teilen', 'Share', 'Partager', 'Compartir', 'Condividi', 'Delen',
    'Udostępnij', 'Bagikan', 'Paylaş', 'Partekatu', 'مشاركة', '分享'];

  let letzterLink = null;
  let spur = null;

  const adresse = (link) => ZIEL + '?link=' + encodeURIComponent(link);

  /* ---- 1. Zwischenablage mitlesen ------------------------------------------------ */
  const original = navigator.clipboard && navigator.clipboard.writeText;
  if (original) {
    navigator.clipboard.writeText = function (text, ...rest) {
      try {
        if (MUSTER.test(String(text))) {
          letzterLink = String(text);
          zeigeSpur(letzterLink);
        }
      } catch (fehler) { /* den Teilen-Weg niemals stören */ }
      return original.call(navigator.clipboard, text, ...rest);
    };
  }

  /* ---- 2. Hinweis mit Ablege-Link ------------------------------------------------- */
  function spurBauen() {
    if (spur && spur.isConnected) return spur;
    spur = document.createElement('div');
    spur.setAttribute(MARKE, 'spur');
    spur.style.cssText = 'position:fixed;right:1rem;bottom:1rem;z-index:2147483000;'
      + 'max-width:min(22rem,90vw);background:#16181d;color:#f4f4f5;'
      + 'border:1px solid rgba(255,255,255,.18);border-radius:.6rem;'
      + 'box-shadow:0 6px 24px rgba(0,0,0,.35);font:14px/1.45 system-ui,sans-serif;'
      + 'padding:.6rem .75rem;display:flex;gap:.5rem;align-items:center';
    document.body.appendChild(spur);
    return spur;
  }

  function zeigeSpur(link) {
    const kasten = spurBauen();
    kasten.innerHTML = '';
    const text = document.createElement('span');
    text.textContent = 'Quiz geteilt:';
    const a = document.createElement('a');
    a.href = adresse(link);
    a.target = '_blank';
    a.rel = 'noopener';
    a.textContent = 'In Fuizstash ablegen';
    a.style.cssText = 'color:#7dd3fc;text-decoration:underline;white-space:nowrap';
    const weg = document.createElement('button');
    weg.type = 'button';
    weg.textContent = '\u00d7';
    weg.setAttribute('aria-label', 'Hinweis schließen');
    weg.style.cssText = 'background:none;border:0;color:inherit;cursor:pointer;'
      + 'font-size:1.15em;line-height:1;padding:0 .1em';
    weg.addEventListener('click', () => kasten.remove());
    kasten.append(text, a, weg);
    clearTimeout(kasten._takt);
    kasten._takt = setTimeout(() => kasten.remove(), 30000);
  }

  function zeigeMeldung(text) {
    const kasten = spurBauen();
    kasten.innerHTML = '';
    const span = document.createElement('span');
    span.textContent = text;
    const weg = document.createElement('button');
    weg.type = 'button';
    weg.textContent = '\u00d7';
    weg.setAttribute('aria-label', 'Hinweis schließen');
    weg.style.cssText = 'background:none;border:0;color:inherit;cursor:pointer;'
      + 'font-size:1.15em;line-height:1;padding:0 .1em';
    weg.addEventListener('click', () => kasten.remove());
    kasten.append(span, weg);
    clearTimeout(kasten._takt);
    kasten._takt = setTimeout(() => kasten.remove(), 15000);
  }

  /* ---- 3. Eintrag im Optionen-Menü ------------------------------------------------ */
  function istTeilenEintrag(knopf) {
    const beschriftung = (knopf.textContent || '').trim();
    return TEILEN.some((wort) => beschriftung === wort);
  }

  function eintragEinfuegen(menue) {
    if (menue.querySelector('[' + MARKE + ']')) return;
    const eintraege = [...menue.querySelectorAll('button')]
      .filter((b) => !b.hasAttribute(MARKE) && istTeilenEintrag(b));
    if (!eintraege.length) return; // anderes Menü — nicht anfassen
    const vorlage = eintraege[0];
    const knopf = vorlage.cloneNode(true); // Aussehen der Umgebung übernehmen
    knopf.setAttribute(MARKE, '1');
    const beschriftung = knopf.querySelector('span') || knopf;
    // Eigenes Symbol: Häkchen/Datenablage statt Teilen-Symbol wäre schöner, doch das
    // Symbol kommt aus einem Svelte-Bauteil — deshalb das vorhandene übernehmen.
    beschriftung.textContent = 'In Fuizstash ablegen';
    knopf.addEventListener('click', (ereignis) => {
      ereignis.preventDefault();
      ereignis.stopPropagation();
      ablegen(menue);
    }, true);
    vorlage.parentNode.insertBefore(knopf, vorlage); // direkt neben dem Original
  }

  async function ablegen(menue) {
    const vorher = letzterLink;
    const fenster = window.open('', '_blank'); // sofort öffnen, sonst blockt der Browser
    const echte = [...menue.querySelectorAll('button')]
      .filter((b) => !b.hasAttribute(MARKE) && istTeilenEintrag(b));
    if (!echte.length) {
      if (fenster) fenster.close();
      return;
    }
    echte[0].click(); // fuiz teilt nun selbst und legt den Link in die Zwischenablage
    const link = await warteAufLink(vorher);
    if (link) {
      if (fenster) fenster.location.replace(adresse(link));
      else window.open(adresse(link), '_blank');
    } else {
      if (fenster) fenster.close();
      zeigeMeldung('Teilen hat nicht geklappt. Bitte in fuiz auf „Teilen" gehen '
        + 'und den Link dort von Hand kopieren.');
    }
  }

  function warteAufLink(vorher) {
    const ende = Date.now() + WARTEZEIT;
    return new Promise((fertig) => {
      const takt = setInterval(() => {
        if (letzterLink && letzterLink !== vorher) {
          clearInterval(takt);
          fertig(letzterLink);
        } else if (Date.now() > ende) {
          clearInterval(takt);
          fertig(null);
        }
      }, 150);
    });
  }

  /* ---- 4. Beobachter --------------------------------------------------------------- */
  function durchsehen() {
    document.querySelectorAll('div.dropdown').forEach(eintragEinfuegen);
  }

  new MutationObserver(durchsehen)
    .observe(document.documentElement, { childList: true, subtree: true });
  if (document.readyState === 'loading') {
    addEventListener('DOMContentLoaded', durchsehen);
  } else {
    durchsehen();
  }
})();
