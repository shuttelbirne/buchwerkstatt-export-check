import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_export import inspect_export, HEADER, INTRO_V2, INTRO_V3, FOOTER

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (ROOT / "examples/fiktiver-entwurf.txt").read_bytes()
CURRENT = (ROOT / "examples/fiktiver-entwurf-txt3.txt").read_bytes()


class ExportTests(unittest.TestCase):
    def test_actual_current_browser_download_with_emoji_and_embedded_label(self):
        report = inspect_export(CURRENT)
        self.assertEqual(report["variant"], "txt-3")
        self.assertEqual(report["open_sections"], 0)
        # The real browser stores22UTF-16 units for this21-codepoint title.
        self.assertEqual([s["characters"] for s in report["sections"]],
                         [21, 67, 47, 33, 81])
        self.assertEqual([s["words"] for s in report["sections"]], [4, 7, 5, 6, 14])
        output = json.dumps(report, ensure_ascii=False)
        for private_text in ("Fiktiv – Stadtkarte", "Diese Zeile gehört zum Text"):
            self.assertNotIn(private_text, output)

    def test_current_bom_crlf_preserves_counts_and_raw_byte_fingerprint_scope(self):
        other = b"\xef\xbb\xbf" + CURRENT.replace(b"\n", b"\r\n")
        original, changed = inspect_export(CURRENT), inspect_export(other)
        self.assertEqual(original["sections"], changed["sections"])
        self.assertNotEqual(original["sha256"], changed["sha256"])

    def test_current_literal_placeholder_and_whitespace_remain_own_text(self):
        raw = (HEADER + "\n" + INTRO_V3
               + "\nAbschnittslängen: [0,12,2,0,3]\n\n"
               + "ARBEITSTITEL\n\n\nBUCHIDEE\n(noch offen)\n\n"
               + "LESERSCHAFT\n  \n\nKAPITELPLAN\n\n\nTEXTENTWURF\n x \n\n"
               + "\n".join(FOOTER) + "\n").encode()
        report = inspect_export(raw)
        self.assertEqual(report["open_sections"], 2)
        self.assertEqual([s["characters"] for s in report["sections"]], [0, 12, 2, 0, 3])
        self.assertFalse(report["sections"][1]["open"])

    def test_current_bad_length_metadata_never_falls_back_to_guessing(self):
        for lengths in (b"[21,67,47,33,82]", b"[22,67,47,33,81]",
                        b"[-1,67,47,33,82]", b"[true,67,47,33,82]",
                        b"[22.0,67,47,33,82]", b"[22,67,47,33]",
                        b"[2097153,67,47,33,82]", b"{\"0\":22}", b"null"):
            with self.subTest(lengths=lengths), self.assertRaisesRegex(ValueError, "Abschnittslängen"):
                inspect_export(CURRENT.replace(b"[22,67,47,33,82]", lengths))

    def test_current_modified_content_and_broken_boundaries_are_rejected(self):
        for raw in (CURRENT.replace("Stadtkarte".encode(), b"Stadtkarte!"),
                    CURRENT.replace(b"\n\nLESERSCHAFT", b"\nLESERSCHAFT"),
                    CURRENT.replace(b"\n\nTEXTENTWURF", b"\n\nUNBEKANNT"),
                    CURRENT[:-100]):
            with self.subTest(raw=raw[:10]), self.assertRaises(ValueError):
                inspect_export(raw)

    def test_txt2_keeps_literal_placeholder_and_empty_fields_distinct(self):
        raw = (HEADER + "\n" + INTRO_V2 + "\n\n"
               + "ARBEITSTITEL\nTitel\n\nBUCHIDEE\n(noch offen)\n\n"
               + "LESERSCHAFT\n\n\nKAPITELPLAN\n Plan \n\nTEXTENTWURF\nText\n\n"
               + "\n".join(FOOTER) + "\n").encode()
        report = inspect_export(raw)
        self.assertEqual(report["variant"], "txt-2")
        self.assertEqual(report["open_sections"], 1)
        self.assertEqual([s["characters"] for s in report["sections"]], [5, 12, 0, 6, 4])
        with self.assertRaisesRegex(ValueError, "mehrdeutig"):
            inspect_export(raw.replace(b"Text\n\n", b"Text\nBUCHIDEE\n\n"))

    def test_chapter_txt_is_reported_as_unsupported_not_as_missing_text(self):
        raw = CURRENT.replace(INTRO_V3.encode(),
                              "Arbeitsstand aus dem Schreibplatz · Mit Kapiteln".encode())
        with self.assertRaisesRegex(ValueError, "bedeutet keinen Textverlust"):
            inspect_export(raw)

    def test_cli_current_download_does_not_mutate_or_expose_input(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "private-name.txt"
            file.write_bytes(CURRENT)
            for raw, code in ((CURRENT, 0), (CURRENT.replace(b"[22,67,47,33,82]", b"[21,67,47,33,82]"), 2)):
                file.write_bytes(raw)
                result = subprocess.run([sys.executable, str(ROOT / "check_export.py"), str(file), "--json"], capture_output=True, text=True)
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertEqual(file.read_bytes(), raw)
                self.assertNotIn(str(file), result.stdout + result.stderr)
                self.assertNotIn("Fiktiv – Stadtkarte", result.stdout + result.stderr)

    def test_open_draft_is_valid_and_content_not_returned(self):
        report = inspect_export(SAMPLE)
        self.assertEqual(report["open_sections"], 1)
        self.assertEqual(len(report["sections"]), 5)
        self.assertNotIn("Meine Unterlagen", json.dumps(report))

    def test_bom_crlf_keeps_counts_but_changes_byte_fingerprint(self):
        changed = b"\xef\xbb\xbf" + SAMPLE.replace(b"\n", b"\r\n")
        first, second = inspect_export(SAMPLE), inspect_export(changed)
        self.assertEqual(first["sections"], second["sections"])
        self.assertNotEqual(first["sha256"], second["sha256"])

    def test_ambiguous_marker_in_manuscript_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "mehrdeutig"):
            inspect_export(SAMPLE.replace(b"(noch offen)", b"BUCHIDEE\nPrivater Text"))

    def test_missing_footer_or_section_is_rejected(self):
        for changed in (SAMPLE.replace(b"LESERSCHAFT\n", b""), SAMPLE[:-80]):
            with self.assertRaises(ValueError):
                inspect_export(changed)

    def test_corrupt_or_oversized_input_is_rejected(self):
        for changed in (b"\xff", SAMPLE + b"\x00", b"x" * (2 * 1024 * 1024 + 1)):
            with self.assertRaises(ValueError):
                inspect_export(changed)

    def test_cli_reads_without_changing_bytes_and_does_not_echo_content(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "private-file.txt"
            file.write_bytes(SAMPLE)
            result = subprocess.run([sys.executable, str(ROOT / "check_export.py"), str(file), "--json"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["valid"])
            self.assertEqual(file.read_bytes(), SAMPLE)
            self.assertNotIn("Meine Unterlagen", result.stdout)
            self.assertNotIn(str(file), result.stdout + result.stderr)

    def test_missing_file_exit_two_without_private_path(self):
        result = subprocess.run([sys.executable, str(ROOT / "check_export.py"), "/not/a/real/private/file", "--json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["valid"])
        self.assertNotIn("/not/a/real", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
