"""
Raport z notatki w jednym miejscu — używany przez bota i aplikację webową.

Wcześniej układ raportu istniał w dwóch niezależnych kopiach (generate_pdf
w bocie i generate_email_html w aplikacji webowej), które trzeba było zmieniać
równolegle. Tutaj jest jedno źródło prawdy.
"""
import json

KATEGORIE_BLOKOW = (
    ("postepy", "Postępy"),
    ("wyzwania", "Wyzwania"),
    ("kroki", "Kolejne kroki"),
)


def _lista(wartosc):
    """Sekcja z bazy (JSON w TEXT) albo już gotowa lista."""
    if not wartosc:
        return []
    if isinstance(wartosc, str):
        try:
            wartosc = json.loads(wartosc)
        except (json.JSONDecodeError, TypeError):
            return [wartosc]
    return wartosc if isinstance(wartosc, list) else []


def _pole(zrodlo, nazwa):
    return _lista(zrodlo.get(nazwa) if isinstance(zrodlo, dict)
                  else getattr(zrodlo, nazwa, None))


def _wartosc(zrodlo, nazwa, domyslna=""):
    v = zrodlo.get(nazwa) if isinstance(zrodlo, dict) else getattr(zrodlo, nazwa, None)
    return v if v not in (None, "") else domyslna


def zadania_wg_osob(zadania):
    """
    Grupuje zadania po osobie odpowiedzialnej, nieprzypisane na końcu.

    Przyjmuje wiersze Zadanie z bazy albo słowniki {osoba, tresc, czas}.
    """
    grupy = {}
    for z in zadania or []:
        if isinstance(z, dict):
            osoba = z.get("osoba") or "Nieprzypisane"
            wpis = {"tresc": z.get("tresc") or "", "czas": z.get("czas"),
                    "wykonane": False}
        else:
            osoba = getattr(z, "osoba", None) or "Nieprzypisane"
            wpis = {"tresc": z.zadanie, "czas": getattr(z, "czas_w_nagraniu", None),
                    "wykonane": bool(getattr(z, "wykonane", False))}
        if wpis["tresc"]:
            grupy.setdefault(osoba, []).append(wpis)

    if "Nieprzypisane" in grupy:                    # nieprzypisane zawsze na końcu
        grupy["Nieprzypisane"] = grupy.pop("Nieprzypisane")
    return grupy


def markdown_notatki(notatka, data_utworzenia=None):
    """
    Raport w Markdownie — czytelny bez żadnego renderera i gotowy do wklejenia
    w dowolne narzędzie, które Markdown rozumie.
    """
    w = []
    temat = _wartosc(notatka, "temat", "Notatka")
    w.append(f"# {temat}\n")

    meta = []
    if data_utworzenia:
        meta.append(f"**Data:** {data_utworzenia}")
    kategoria = _wartosc(notatka, "kategoria")
    if kategoria:
        meta.append(f"**Kategoria:** {kategoria}")
    rozmowcy = _pole(notatka, "rozmowcy")
    if rozmowcy:
        etykiety = ", ".join(r.get("mowca", "") for r in rozmowcy if isinstance(r, dict))
        meta.append(f"**Rozmówcy:** {etykiety}")
    if meta:
        w.append(" · ".join(meta) + "\n")

    opis = _wartosc(notatka, "opis")
    if opis:
        w.append(f"## Podsumowanie\n\n{opis}\n")

    if rozmowcy:
        w.append("## Kto co mówił\n")
        for r in rozmowcy:
            if isinstance(r, dict):
                w.append(f"- **{r.get('mowca', 'Rozmówca')}:** {r.get('podsumowanie', '')}")
        w.append("")

    bloki = _pole(notatka, "bloki")
    for kat, naglowek in KATEGORIE_BLOKOW:
        wybrane = [b for b in bloki if isinstance(b, dict) and b.get("kategoria") == kat]
        if not wybrane:
            continue
        w.append(f"## {naglowek}\n")
        for b in wybrane:
            czas = f" ({b['czas']})" if b.get("czas") else ""
            w.append(f"### {b.get('tytul', 'Wątek')}{czas}\n")
            w += [f"- {pkt}" for pkt in b.get("punkty", [])]
            w.append("")

    grupy = zadania_wg_osob(_pole(notatka, "zadania") or getattr(notatka, "zadania", []))
    if grupy:
        w.append("## Zadania\n")
        for osoba, lista in grupy.items():
            w.append(f"### {osoba}\n")
            for z in lista:
                znak = "x" if z["wykonane"] else " "
                czas = f" *({z['czas']})*" if z.get("czas") else ""
                w.append(f"- [{znak}] {z['tresc']}{czas}")
            w.append("")

    for nazwa, naglowek in (("kluczowe_mysli", "Główne myśli i tematy"),
                            ("decyzje", "Decyzje i wnioski"),
                            ("terminy", "Terminy"),
                            ("otwarte_watki", "Do rozważenia")):
        elementy = _pole(notatka, nazwa)
        if not elementy:
            continue
        w.append(f"## {naglowek}\n")
        for x in elementy:
            if isinstance(x, dict):
                w.append(f"- **{x.get('watek', 'Wątek')}:** {x.get('tresc', '')}")
            else:
                w.append(f"- {x}")
        w.append("")

    w.append("---\n*Wygenerowano przez Voice Notes Bot*")
    return "\n".join(w)


def _esc(x):
    return (str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def html_notatki(notatka, data_utworzenia=None):
    """Ten sam raport w HTML — źródło dla PDF-a generowanego przez WeasyPrint."""
    h = ['<!DOCTYPE html><html lang="pl"><head><meta charset="utf-8"><style>',
         """
         @page { size: A4; margin: 18mm 16mm; }
         body { font-family: "DejaVu Sans", sans-serif; font-size: 10.5pt;
                line-height: 1.5; color: #1b2129; }
         h1 { font-size: 19pt; color: #1f7a4d; margin: 0 0 4px; }
         h2 { font-size: 13pt; color: #1668b0; margin: 20px 0 6px;
              border-bottom: 1px solid #d5dde5; padding-bottom: 4px;
              page-break-after: avoid; }
         h3 { font-size: 11pt; margin: 12px 0 4px; page-break-after: avoid; }
         .meta { color: #5a6675; font-size: 9pt; margin-bottom: 14px; }
         .czas { color: #7a8695; font-weight: normal; }
         ul { margin: 4px 0 8px; padding-left: 18px; }
         li { margin-bottom: 4px; }
         section { page-break-inside: avoid; }
         footer { margin-top: 26px; padding-top: 10px; border-top: 1px solid #d5dde5;
                  color: #8a94a3; font-size: 8.5pt; text-align: center; }
         """, '</style></head><body>']

    h.append(f"<h1>{_esc(_wartosc(notatka, 'temat', 'Notatka'))}</h1>")

    meta = []
    if data_utworzenia:
        meta.append(_esc(data_utworzenia))
    if _wartosc(notatka, "kategoria"):
        meta.append(_esc(_wartosc(notatka, "kategoria")))
    rozmowcy = _pole(notatka, "rozmowcy")
    if rozmowcy:
        meta.append(", ".join(_esc(r.get("mowca", "")) for r in rozmowcy if isinstance(r, dict)))
    if meta:
        h.append(f"<p class='meta'>{' &middot; '.join(meta)}</p>")

    if _wartosc(notatka, "opis"):
        h.append(f"<section><h2>Podsumowanie</h2><p>{_esc(_wartosc(notatka, 'opis'))}</p></section>")

    if rozmowcy:
        h.append("<section><h2>Kto co mówił</h2><ul>")
        h += [f"<li><strong>{_esc(r.get('mowca', 'Rozmówca'))}:</strong> "
              f"{_esc(r.get('podsumowanie', ''))}</li>"
              for r in rozmowcy if isinstance(r, dict)]
        h.append("</ul></section>")

    bloki = _pole(notatka, "bloki")
    for kat, naglowek in KATEGORIE_BLOKOW:
        wybrane = [b for b in bloki if isinstance(b, dict) and b.get("kategoria") == kat]
        if not wybrane:
            continue
        h.append(f"<section><h2>{naglowek}</h2>")
        for b in wybrane:
            czas = f" <span class='czas'>{_esc(b['czas'])}</span>" if b.get("czas") else ""
            h.append(f"<h3>{_esc(b.get('tytul', 'Wątek'))}{czas}</h3><ul>")
            h += [f"<li>{_esc(p)}</li>" for p in b.get("punkty", [])]
            h.append("</ul>")
        h.append("</section>")

    grupy = zadania_wg_osob(_pole(notatka, "zadania") or getattr(notatka, "zadania", []))
    if grupy:
        h.append("<section><h2>Zadania</h2>")
        for osoba, lista in grupy.items():
            h.append(f"<h3>{_esc(osoba)}</h3><ul>")
            for z in lista:
                czas = f" <span class='czas'>{_esc(z['czas'])}</span>" if z.get("czas") else ""
                h.append(f"<li>{'☑' if z['wykonane'] else '☐'} {_esc(z['tresc'])}{czas}</li>")
            h.append("</ul>")
        h.append("</section>")

    for nazwa, naglowek in (("kluczowe_mysli", "Główne myśli i tematy"),
                            ("decyzje", "Decyzje i wnioski"),
                            ("terminy", "Terminy"),
                            ("otwarte_watki", "Do rozważenia")):
        elementy = _pole(notatka, nazwa)
        if not elementy:
            continue
        h.append(f"<section><h2>{naglowek}</h2><ul>")
        for x in elementy:
            if isinstance(x, dict):
                h.append(f"<li><strong>{_esc(x.get('watek', 'Wątek'))}:</strong> "
                         f"{_esc(x.get('tresc', ''))}</li>")
            else:
                h.append(f"<li>{_esc(x)}</li>")
        h.append("</ul></section>")

    h.append("<footer>Wygenerowano przez Voice Notes Bot</footer></body></html>")
    return "".join(h)
