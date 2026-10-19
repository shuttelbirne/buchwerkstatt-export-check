#!/usr/bin/env python3
"""Read-only structural check for the Rauschwerk writing-workspace TXT export."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HEADER = "RAUSCHWERK · MEIN BUCHENTWURF"
INTRO = "Arbeitsstand aus dem Schreibplatz · Eigene Eingaben"
INTRO_V2 = INTRO + " · TXT 2"
INTRO_V3 = INTRO + " · TXT 3"
INTRO_CHAPTERS = "Arbeitsstand aus dem Schreibplatz · Mit Kapiteln"
FIELDS = ("ARBEITSTITEL", "BUCHIDEE", "LESERSCHAFT", "KAPITELPLAN", "TEXTENTWURF")
FOOTER = (
    "Dieser Export enthält deine Eingaben. Er ist ein Arbeitsentwurf und keine KI-Auswertung oder Veröffentlichungszusage.",
    "https://rauschwerkverlag.de/buchwerkstatt/",
)
MAX_BYTES = 2 * 1024 * 1024


def _length_framed_values(text):
    """Read TXT 3 lengths as JavaScript UTF-16 units, not Python characters."""
    header = HEADER + "\n" + INTRO_V3 + "\n"
    footer = "\n\n" + "\n".join(FOOTER)
    if not text.endswith(footer):
        raise ValueError("Der Abschluss des TXT-3-Exports fehlt bzw. wurde verändert.")
    end = text.find("\n\n", len(header))
    metadata = text[len(header):end]
    prefix = "Abschnittslängen: "
    try:
        if end < 0 or not metadata.startswith(prefix):
            raise ValueError()
        lengths = json.loads(metadata[len(prefix):])
        if (not isinstance(lengths, list) or len(lengths) != len(FIELDS)
                or any(type(n) is not int or n < 0 or n > MAX_BYTES for n in lengths)):
            raise ValueError()
    except (ValueError, json.JSONDecodeError):
        raise ValueError("Die fünf Abschnittslängen des TXT-3-Exports sind nicht lesbar.") from None
    body = text[end + 2:-len(footer)].encode("utf-16-le")
    offset, values = 0, []
    try:
        for index, (label, length) in enumerate(zip(FIELDS, lengths)):
            marker = (label + "\n").encode("utf-16-le")
            if not body.startswith(marker, offset):
                raise ValueError()
            offset += len(marker)
            stop = offset + length * 2
            if stop > len(body):
                raise ValueError()
            values.append(body[offset:stop].decode("utf-16-le"))
            offset = stop
            if index < len(FIELDS) - 1:
                if body[offset:offset + 4] != b"\n\x00\n\x00":
                    raise ValueError()
                offset += 4
        if offset != len(body):
            raise ValueError()
    except (ValueError, UnicodeDecodeError):
        raise ValueError("TXT-3-Abschnitte und gespeicherte Längen stimmen nicht überein. Originaldatei behalten und manuell prüfen.") from None
    return values


def inspect_export(raw):
    """Return counts and a byte fingerprint; never return manuscript content."""
    if len(raw) > MAX_BYTES:
        raise ValueError("Datei größer als 2 MiB; Prüfung abgebrochen.")
    if raw.startswith(b"PK\x03\x04"):
        raise ValueError("ZIP-/DOCX-Dateien werden nicht unterstützt. Benötigt wird ein TXT-Export mit fünf Werkstattabschnitten.")
    if raw.startswith(b"%PDF-"):
        raise ValueError("PDF-Dateien werden nicht unterstützt. Benötigt wird ein TXT-Export mit fünf Werkstattabschnitten.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("Keine gültige UTF-8-Textdatei.") from None
    if "\x00" in text:
        raise ValueError("Die Datei enthält Nullbytes.")
    if text.lstrip().startswith("{"):
        try:
            project = json.loads(text)
        except ValueError:
            project = None
        if isinstance(project, dict) and project.get("format") == "rauschwerk-autorenwerkstatt":
            raise ValueError("Buchwerkstatt-Projektdatei erkannt; dieser Prüfer wertet keine Projekt-JSON-Dateien aus. Projekt mit Kapiteln und Fassungen in der Buchwerkstatt öffnen.")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    if lines[:2] == [HEADER, INTRO_CHAPTERS]:
        raise ValueError("Kapitel-TXT erkannt; dieser Prüfer wertet nur die fünf Werkstattabschnitte aus. Kapitel und Fassungen mit der Projektdatei in der Buchwerkstatt prüfen.")
    if (lines[:1] != [HEADER] or len(lines) < 2
            or lines[1] not in (INTRO, INTRO_V2, INTRO_V3)
            or tuple(lines[-2:]) != FOOTER):
        raise ValueError("Kein unterstützter Fünf-Abschnitt-TXT-Export erkannt: Format unbekannt oder Kopf/Abschluss verändert. Ein reiner Manuskripttext ist ein anderes Format und wird hier nicht geprüft.")
    version = {INTRO: "legacy-20261008", INTRO_V2: "txt-2", INTRO_V3: "txt-3"}[lines[1]]
    if lines[1] == INTRO_V3:
        values = _length_framed_values("\n".join(lines))
    else:
        body = lines[2:-2]
        markers = [(i, line) for i, line in enumerate(body) if line in FIELDS]
        if tuple(label for _, label in markers) != FIELDS:
            raise ValueError("Die fünf Abschnittsmarken fehlen, sind vertauscht oder mehrdeutig. Auch eine gleichlautende Zeile im eigenen Text kann der Grund sein.")
        if any(line.strip() for line in body[:markers[0][0]]):
            raise ValueError("Unerwarteter Text vor dem ersten Abschnitt.")
        values = ["\n".join(body[index + 1:markers[pos + 1][0] if pos + 1 < len(markers) else len(body)]).strip()
                  for pos, (index, _) in enumerate(markers)]
    sections = []
    for label, value in zip(FIELDS, values):
        is_open = not value.strip() or (version == "legacy-20261008" and value == "(noch offen)")
        sections.append({"section": label, "open": is_open,
                         "characters": 0 if is_open else len(value),
                         "words": 0 if is_open else len(value.split())})
    return {"format": "rauschwerk-workspace-txt", "format_version": version,
            "coverage": "five-workspace-sections", "bytes": len(raw),
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
        print("Struktur erkannt · fünf Abschnitte · " + report["format_version"] + " · Datei unverändert")
        for section in report["sections"]:
            state = "noch offen" if section["open"] else f'{section["words"]} Wörter · {section["characters"]} Zeichen'
            print(f'{section["section"]}: {state}')
        print("SHA-256: " + report["sha256"])
        print("Strukturprüfung; keine Inhalts-, Beleg- oder Veröffentlichungsfreigabe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
