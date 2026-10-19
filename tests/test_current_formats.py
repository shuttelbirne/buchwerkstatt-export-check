import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_export import inspect_export, INTRO, INTRO_V2

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = json.loads((Path(__file__).parent / "live_export_fixtures.json").read_text())


def changed_lengths(text, transform):
    lines = text.splitlines()
    lengths = json.loads(lines[2].split(": ", 1)[1])
    lines[2] = "Abschnittslängen: " + json.dumps(transform(lengths), separators=(",", ":"))
    return ("\n".join(lines) + "\n").encode()


class CurrentFormatsTests(unittest.TestCase):
    def test_actual_export_function_cases_match_all_five_input_values(self):
        for name in ("current", "markers", "empty", "literal_placeholder", "whitespace"):
            with self.subTest(case=name):
                fixture = FIXTURES[name]
                raw = fixture["text"].encode()
                report = inspect_export(raw)
                self.assertEqual(report["format_version"], "txt-3")
                self.assertEqual(report["coverage"], "five-workspace-sections")
                for section, value in zip(report["sections"], fixture["values"]):
                    is_open = not value.strip()
                    self.assertEqual(section["open"], is_open)
                    self.assertEqual(section["characters"], 0 if is_open else len(value))
                    self.assertEqual(section["words"], 0 if is_open else len(value.split()))
                self.assertEqual(report["sha256"], hashlib.sha256(raw).hexdigest())

    def test_utf16_metadata_accepts_emoji_and_rejects_codepoint_length(self):
        fixture = FIXTURES["current"]
        self.assertNotEqual(len(fixture["values"][-1]), len(fixture["values"][-1].encode("utf-16-le")) // 2)
        wrong = changed_lengths(fixture["text"], lambda lengths: lengths[:-1] + [len(fixture["values"][-1])])
        with self.assertRaisesRegex(ValueError, "Längen stimmen nicht"):
            inspect_export(wrong)

    def test_missing_or_invalid_length_metadata_never_uses_legacy_fallback(self):
        text = FIXTURES["current"]["text"]
        for metadata in ("", "[]", "null", "[1,2,3,4]", "[true,1,1,1,1]", "[-1,1,1,1,1]", "[1.0,1,1,1,1]", "[999999999,1,1,1,1]"):
            with self.subTest(metadata=metadata):
                lines = text.splitlines()
                lines[2] = "Abschnittslängen: " + metadata
                with self.assertRaisesRegex(ValueError, "Abschnittslängen"):
                    inspect_export(("\n".join(lines) + "\n").encode())

    def test_changed_boundaries_or_added_body_are_rejected(self):
        text = FIXTURES["current"]["text"]
        for raw in (
            changed_lengths(text, lambda lengths: [lengths[0] + 1] + lengths[1:]),
            text.replace("\nTEXTENTWURF\n", "\nTEXTENTWURF-X\n").encode(),
            text.replace("Text mit ä und 📖.", "Text mit ä und 📖. Zusatz").encode(),
            text.replace("\n\nBUCHIDEE\n", "\nBUCHIDEE\n").encode(),
        ):
            with self.subTest(raw_sha=hashlib.sha256(raw).hexdigest()):
                with self.assertRaises(ValueError):
                    inspect_export(raw)

    def test_crlf_and_bom_keep_v3_counts_and_hash_original_bytes(self):
        raw = FIXTURES["markers"]["text"].encode()
        other = b"\xef\xbb\xbf" + raw.replace(b"\n", b"\r\n")
        first, second = inspect_export(raw), inspect_export(other)
        self.assertEqual(first["sections"], second["sections"])
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.assertEqual(second["sha256"], hashlib.sha256(other).hexdigest())

    def test_literal_placeholder_in_txt2_is_content_but_legacy_is_open(self):
        legacy = (ROOT / "examples/fiktiver-entwurf.txt").read_bytes()
        previous = legacy.replace(INTRO.encode(), INTRO_V2.encode(), 1)
        self.assertEqual(inspect_export(legacy)["open_sections"], 1)
        self.assertEqual(inspect_export(previous)["open_sections"], 0)
        self.assertEqual(inspect_export(previous)["format_version"], "txt-2")

    def test_actual_chapter_format_is_explicitly_unsupported(self):
        with self.assertRaisesRegex(ValueError, "Kapitel-TXT erkannt"):
            inspect_export(FIXTURES["chapters"]["text"].encode())

    def test_unknown_future_version_is_not_accepted(self):
        with self.assertRaises(ValueError):
            inspect_export(FIXTURES["current"]["text"].replace("TXT 3", "TXT 4", 1).encode())

    def test_zip_or_docx_gets_specific_scope_error(self):
        with self.assertRaisesRegex(ValueError, "ZIP-/DOCX"):
            inspect_export(b"PK\x03\x04\xff\x00binary")

    def test_pdf_and_project_files_get_specific_scope_error(self):
        with self.assertRaisesRegex(ValueError, "PDF-Dateien"):
            inspect_export(b"%PDF-1.7\xffbinary")
        with self.assertRaisesRegex(ValueError, "Projektdatei erkannt"):
            inspect_export(json.dumps({"format": "rauschwerk-autorenwerkstatt", "version": 2}).encode())

    def test_plain_manuscript_is_outside_scope_without_claim_of_corruption(self):
        with self.assertRaisesRegex(ValueError, "reiner Manuskripttext ist ein anderes Format"):
            inspect_export("Fiktives Buch\n\nFiktiver vollständiger Absatz.\n".encode())

    def test_cli_current_input_read_only_and_no_private_content_or_path(self):
        fixture = FIXTURES["markers"]
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "private-manuscript-name.txt"
            raw = fixture["text"].encode()
            file.write_bytes(raw)
            result = subprocess.run([sys.executable, str(ROOT / "check_export.py"), str(file), "--json"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["format_version"], "txt-3")
            self.assertEqual(file.read_bytes(), raw)
            self.assertNotIn(str(file), result.stdout + result.stderr)
            self.assertNotIn("Eigene Einrückung", result.stdout + result.stderr)

    def test_cli_chapter_input_has_exit_two_and_no_content(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "private-chapters.txt"
            file.write_text(FIXTURES["chapters"]["text"])
            result = subprocess.run([sys.executable, str(ROOT / "check_export.py"), str(file), "--json"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            report = json.loads(result.stdout)
            self.assertFalse(report["valid"])
            self.assertIn("Kapitel-TXT erkannt", report["error"])
            self.assertNotIn(str(file), result.stdout + result.stderr)
            self.assertNotIn("Kein Nutzermanuskript", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
