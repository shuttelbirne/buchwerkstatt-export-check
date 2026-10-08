#!/usr/bin/env python3
"""Read-only structural check for the Rauschwerk writing-workspace TXT export."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HEADER = "RAUSCHWERK · MEIN BUCHENTWURF"
INTRO = "Arbeitsstand aus dem Schreibplatz · Eigene Eingaben"
FIELDS = ("ARBEITSTITEL", "BUCHIDEE", "LESERSCHAFT", "KAPITELPLAN", "TEXTENTWURF")
FOOTER = (
    "Dieser Export enthält deine Eingaben. Er ist ein Arbeitsentwurf und keine KI-Auswertung oder Veröffentlichungszusage.",
    "https://rauschwerkverlag.de/buchwerkstatt/",
)
MAX_BYTES = 2 * 1024 * 1024


def inspect_export(raw):
    """Return counts and a byte fingerprint; never return manuscript content."""
    if len(raw) > MAX_BYTES:
        raise ValueError("Datei größer als 2 MiB; Prüfung abgebrochen.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("Keine gültige UTF-8-Textdatei.") from None
    if "\x00" in text:
        raise ValueError("Die Datei enthält Nullbytes.")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    if lines[:2] != [HEADER, INTRO] or tuple(lines[-2:]) != FOOTER:
        raise ValueError("Kopf oder Abschluss des Werkstatt-Exports fehlt bzw. wurde verändert.")
    body = lines[2:-2]
    markers = [(i, line) for i, line in enumerate(body) if line in FIELDS]
    if tuple(label for _, label in markers) != FIELDS:
        raise ValueError("Die fünf Abschnittsmarken fehlen, sind vertauscht oder mehrdeutig. Auch eine gleichlautende Zeile im eigenen Text kann der Grund sein.")
    if any(line.strip() for line in body[:markers[0][0]]):
        raise ValueError("Unerwarteter Text vor dem ersten Abschnitt.")
    sections = []
    for pos, (index, label) in enumerate(markers):
        end = markers[pos + 1][0] if pos + 1 < len(markers) else len(body)
        value = "\n".join(body[index + 1:end]).strip()
        is_open = not value or value == "(noch offen)"
        sections.append({"section": label, "open": is_open,
                         "characters": 0 if is_open else len(value),
                         "words": 0 if is_open else len(value.split())})
    return {"format": "rauschwerk-workspace-txt", "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(), "sections": sections,
            "open_sections": sum(s["open"] for s in sections)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Buchwerkstatt-TXT lokal prüfen; keine Uploads, keine Änderungen.")
    parser.add_argument("file", type=Path, help="Gespeicherter TXT-Export")
    parser.add_argument("--json", action="store_true", help="Maschinenlesbare Ausgabe ohne Textauszüge")
    args = parser.parse_args(argv)
    try:
        with args.file.open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
        report = inspect_export(raw)
    except (OSError, ValueError) as exc:
        # Do not expose a private path from an operating-system error.
        message = str(exc) if isinstance(exc, ValueError) else "Datei konnte nicht gelesen werden."
        if args.json:
            print(json.dumps({"valid": False, "error": message}, ensure_ascii=False))
        else:
            print("Prüfung abgebrochen: " + message, file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"valid": True, **report}, ensure_ascii=False, indent=2))
    else:
        print("Struktur erkannt · fünf Abschnitte · Datei unverändert")
        for section in report["sections"]:
            state = "noch offen" if section["open"] else f'{section["words"]} Wörter · {section["characters"]} Zeichen'
            print(f'{section["section"]}: {state}')
        print("SHA-256: " + report["sha256"])
        print("Strukturprüfung; keine Inhalts-, Beleg- oder Veröffentlichungsfreigabe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
