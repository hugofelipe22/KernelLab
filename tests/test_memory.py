import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import memory  # noqa: E402

REFS = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5, 2, 1, 5, 3, 2]


class TestMemory(unittest.TestCase):
    def test_enunciado_four_frames(self):
        self.assertEqual((memory.fifo(REFS, 4).hits, memory.fifo(REFS, 4).faults), (5, 12))
        self.assertEqual((memory.lru(REFS, 4).hits, memory.lru(REFS, 4).faults), (7, 10))
        self.assertEqual((memory.optimal(REFS, 4).hits, memory.optimal(REFS, 4).faults), (10, 7))

    def test_fault_rate(self):
        self.assertAlmostEqual(memory.fifo(REFS, 4).fault_rate, 12 / 17)

    def test_hits_plus_faults_equals_references(self):
        for r in memory.run_all(REFS, 4):
            self.assertEqual(r.hits + r.faults, len(REFS))

    def test_optimal_is_lower_bound(self):
        for n in range(1, 8):
            opt = memory.optimal(REFS, n).faults
            self.assertLessEqual(opt, memory.fifo(REFS, n).faults)
            self.assertLessEqual(opt, memory.lru(REFS, n).faults)

    def test_frames_never_exceed_capacity_or_duplicate(self):
        for r in memory.run_all(REFS, 3):
            for st in r.steps:
                pages = [f for f in st.frames if f is not None]
                self.assertEqual(len(st.frames), 3)
                self.assertEqual(len(pages), len(set(pages)))
                self.assertIn(st.ref, pages)

    def test_fifo_state_trace(self):
        r = memory.fifo(REFS, 4)
        self.assertEqual(r.steps[6].frames, [5, 2, 3, 4])   # 5 substitui a página 1
        self.assertEqual(r.steps[6].victim, 1)

    def test_lru_evicts_least_recently_used(self):
        r = memory.lru([1, 2, 3, 1, 4], 3)   # 2 é a menos recente quando 4 chega
        self.assertEqual(r.steps[-1].victim, 2)

    def test_belady_anomaly_for_fifo(self):
        base = REFS[:12]
        self.assertEqual(memory.fifo(base, 3).faults, 9)
        self.assertEqual(memory.fifo(base, 4).faults, 10)  # mais frames, mais faltas

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            memory.fifo(REFS, 0)
        with self.assertRaises(ValueError):
            memory.lru([], 3)


if __name__ == "__main__":
    unittest.main()
