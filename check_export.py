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


def section_counts(label, value, legacy_placeholder=False):
    """Report only names and counts; TXT 2/3 placeholders are actual input."""
    is_open = not value or (legacy_placeholder and value == "(noch offen)")
    return {"section": label, "open": is_open,
            "characters": 0 if is_open else len(value),
            "words": 0 if is_open else len(value.split())}


def inspect_v3(text):
    """Consume the stored JavaScript UTF-16 lengths, not in-text labels."""
    prefix = HEADER + "\n" + INTRO_V3 + "\n"
    end = text.find("\n\n", len(prefix))
    line = text[len(prefix):end]
    try:
        if end < 0 or not line.startswith("Abschnittslängen: ") or len(line) > 256:
            raise ValueError()
        lengths = json.loads(line[len("Abschnittslängen: "):])
        if (not isinstance(lengths, list) or len(lengths) != len(FIELDS)
                or any(type(n) is not int or not 0 <= n <= MAX_BYTES for n in lengths)):
            raise ValueError()
    except (ValueError, RecursionError):
        raise ValueError("Die Abschnittslängen des TXT-3-Exports sind nicht lesbar.") from None

    body = text[end + 2:].encode("utf-16-le")
    offset, sections = 0, []
    mismatch = "Die gespeicherten Abschnittslängen passen nicht zum TXT-3-Inhalt. Originaldatei behalten und manuell vergleichen."
    for pos, label in enumerate(FIELDS):
        marker = (label + "\n").encode("utf-16-le")
        if not body.startswith(marker, offset):
            raise ValueError(mismatch)
        offset += len(marker)
        stop = offset + 2 * lengths[pos]
        if stop > len(body):
            raise ValueError(mismatch)
        try:
            value = body[offset:stop].decode("utf-16-le")
        except UnicodeDecodeError:
            raise ValueError(mismatch) from None
        offset = stop
        sections.append(section_counts(label, value))
        if pos < len(FIELDS) - 1:
            if body[offset:offset + 4] != b"\n\x00\n\x00":
                raise ValueError(mismatch)
            offset += 4
    if body[offset:] != ("\n\n" + "\n".join(FOOTER)).encode("utf-16-le"):
        raise ValueError(mismatch)
    return sections


def inspect_v2(lines):
    """TXT 2 has no lengths; reject every duplicate reserved label."""
    if lines[2:4] != ["", FIELDS[0]]:
        raise ValueError("Die fünf Abschnitte stehen nicht im TXT-2-Exportformat.")
    body = lines[3:-3]
    markers = [(i, line) for i, line in enumerate(body) if line in FIELDS]
    if tuple(label for _, label in markers) != FIELDS:
        raise ValueError("Die fünf Abschnittsmarken fehlen, sind vertauscht oder mehrdeutig.")
    sections = []
    for pos, (index, label) in enumerate(markers):
        end = markers[pos + 1][0] if pos + 1 < len(markers) else len(body)
        if pos < len(markers) - 1:
            if body[end - 1] != "":
                raise ValueError("Der Abschnittstrenner des TXT-2-Exports fehlt.")
            end -= 1
        value = "\n".join(body[index + 1:end])
        sections.append(section_counts(label, value))
    return sections


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
    if lines[:2] == [HEADER, INTRO_CHAPTERS]:
        raise ValueError("Dieser Kapitel-TXT ist ein Weiterbearbeitungsexport, kein unterstützter Fünf-Abschnitt-Export. Das bedeutet keinen Textverlust. Zum Wiederherstellen getrennter Kapitel und Fassungen die Projektdatei verwenden.")
    if (len(lines) < 4 or lines[0] != HEADER
            or lines[1] not in (INTRO, INTRO_V2, INTRO_V3)
            or tuple(lines[-2:]) != FOOTER):
        raise ValueError("Kein unterstützter Struktur-TXT oder veränderter Kopf/Abschluss. Reine Lesemanuskripte und Projektdateien werden hier nicht geprüft.")
    if lines[1] == INTRO_V3:
        sections = inspect_v3("\n".join(lines))
        variant = "txt-3"
    elif lines[1] == INTRO_V2:
        if lines[-3] != "":
            raise ValueError("Der Abschluss-Trenner des TXT-2-Exports fehlt.")
        sections = inspect_v2(lines)
        variant = "txt-2"
    else:
        sections = inspect_legacy(lines)
        variant = "legacy"
    return {"format": "rauschwerk-workspace-txt", "variant": variant,
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "sections": sections, "open_sections": sum(s["open"] for s in sections)}


def inspect_legacy(lines):
    """Keep the original unversioned format's placeholder/whitespace rules."""
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
        sections.append(section_counts(label, value, legacy_placeholder=True))
    return sections


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
