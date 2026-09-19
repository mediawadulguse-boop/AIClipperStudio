import tempfile
import unittest
from pathlib import Path
from ai_clipper.transcript import parse_srt, seconds_to_clock

class TranscriptTests(unittest.TestCase):
    def test_parse_srt(self):
        srt = """1
00:00:01,000 --> 00:00:03,500
Halo dunia.

2
00:00:04,000 --> 00:00:06,000
Ini tes AI Clipper.
"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.srt"
            p.write_text(srt, encoding="utf-8")
            rows = parse_srt(p)
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[0].start, 1.0)
        self.assertEqual(rows[1].text, "Ini tes AI Clipper.")
        self.assertEqual(seconds_to_clock(65), "00:01:05")

if __name__ == "__main__":
    unittest.main()
