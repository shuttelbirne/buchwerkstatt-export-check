import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_export import inspect_export

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = (ROOT / "examples/fiktiver-entwurf.txt").read_bytes()


class ExportTests(unittest.TestCase):
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
