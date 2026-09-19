import unittest
from ai_clipper.models import TranscriptSegment
from ai_clipper.scoring import make_heuristic_candidates

class ScoringTests(unittest.TestCase):
    def test_candidates_are_ranked_and_bounded(self):
        segs = [
            TranscriptSegment(0, 8, "Banyak orang mengira anggarannya lima puluh miliar."),
            TranscriptSegment(8, 16, "Ternyata fakta di dokumennya berbeda."),
            TranscriptSegment(16, 25, "Anggaran sebenarnya dua belas miliar dan ada bukti laporannya."),
            TranscriptSegment(25, 34, "Ini yang tidak banyak orang tahu."),
            TranscriptSegment(34, 44, "Jadi masalah sebenarnya bukan seperti yang beredar."),
        ]
        clips = make_heuristic_candidates(segs, min_seconds=20, max_seconds=75, limit=5)
        self.assertTrue(clips)
        self.assertLessEqual(len(clips), 5)
        self.assertTrue(all(0 <= c.score <= 100 for c in clips))
        self.assertEqual(clips, sorted(clips, key=lambda c: c.score, reverse=True))

if __name__ == "__main__":
    unittest.main()
