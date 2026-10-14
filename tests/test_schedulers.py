import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import metrics  # noqa: E402
import schedulers as sch  # noqa: E402


def enunciado():
    return sch.load_processes(ROOT / "data" / "processes.json")


def seq(result):
    return [(s.pid, s.start, s.end) for s in result.segments]


class TestSchedulers(unittest.TestCase):
    def setUp(self):
        self.ps = enunciado()

    def test_fcfs_order_and_gantt(self):
        r = sch.fcfs(self.ps)
        self.assertEqual(seq(r), [("P1", 0, 8), ("P2", 8, 12), ("P3", 12, 21),
                                  ("P4", 21, 23), ("P5", 23, 35), ("P6", 35, 41)])

    def test_sjf_order(self):
        self.assertEqual(sch.sjf(self.ps).order, ["P1", "P4", "P2", "P6", "P3", "P5"])

    def test_priority_order(self):
        self.assertEqual(sch.priority(self.ps).order, ["P1", "P4", "P2", "P6", "P3", "P5"])

    def test_priority_preemptive_runs_alarm_immediately(self):
        r = sch.priority(self.ps, preemptive=True)
        self.assertEqual(seq(r)[:3], [("P1", 0, 3), ("P4", 3, 5), ("P1", 5, 10)])

    def test_round_robin_q3(self):
        r = sch.round_robin(self.ps, 3)
        self.assertEqual(r.order, ["P1", "P2", "P3", "P4", "P1", "P5", "P6", "P2",
                                   "P3", "P1", "P5", "P6", "P3", "P5"])
        self.assertEqual(r.segments[-1].end, 41)

    def test_all_cpu_time_is_consumed(self):
        for res in sch.run_all(self.ps, 3):
            for p in self.ps:
                run = sum(s.end - s.start for s in res.segments if s.pid == p.pid)
                self.assertEqual(run, p.burst, f"{res.algorithm} {p.pid}")
            for a, b in zip(res.segments, res.segments[1:]):
                self.assertLessEqual(a.end, b.start)      # sem sobreposição

    def test_no_process_runs_before_arrival(self):
        arrival = {p.pid: p.arrival for p in self.ps}
        for res in sch.run_all(self.ps, 3):
            for s in res.segments:
                self.assertGreaterEqual(s.start, arrival[s.pid])

    def test_idle_cpu_gap(self):
        ps = sch.parse_processes([
            {"pid": "A", "arrival": 0, "burst": 2, "priority": 1},
            {"pid": "B", "arrival": 5, "burst": 2, "priority": 1}])
        for fn in (sch.fcfs, sch.sjf, sch.priority, sch.round_robin):
            self.assertEqual(seq(fn(ps)), [("A", 0, 2), ("B", 5, 7)])

    def test_quantum_is_configurable(self):
        q1 = sch.round_robin(self.ps, 1)
        q100 = sch.round_robin(self.ps, 100)
        self.assertGreater(q1.context_switches, q100.context_switches)
        self.assertEqual(q100.order, sch.fcfs(self.ps).order)  # quantum grande = FCFS

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            sch.round_robin(self.ps, 0)
        with self.assertRaises(ValueError):
            sch.parse_processes([{"pid": "A", "arrival": 0, "burst": 0, "priority": 1}])
        with self.assertRaises(ValueError):
            sch.parse_processes([])


class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.ps = enunciado()

    def summary(self, res):
        return metrics.compute_metrics(res, self.ps)

    def test_fcfs_averages(self):
        s = self.summary(sch.fcfs(self.ps))
        self.assertAlmostEqual(s.avg_waiting, 82 / 6)
        self.assertAlmostEqual(s.avg_turnaround, 123 / 6)
        self.assertAlmostEqual(s.avg_response, 82 / 6)
        self.assertEqual(s.context_switches, 5)
        self.assertEqual(s.get("P4").waiting, 18)

    def test_sjf_averages(self):
        s = self.summary(sch.sjf(self.ps))
        self.assertAlmostEqual(s.avg_waiting, 64 / 6)
        self.assertAlmostEqual(s.avg_turnaround, 105 / 6)
        self.assertEqual(s.starving_pids, ["P5"])

    def test_round_robin_averages(self):
        s = self.summary(sch.round_robin(self.ps, 3))
        self.assertAlmostEqual(s.avg_waiting, 108 / 6)
        self.assertAlmostEqual(s.avg_turnaround, 149 / 6)
        self.assertAlmostEqual(s.avg_response, 32 / 6)
        self.assertEqual(s.context_switches, 13)
        self.assertEqual(s.starving_pids, [])

    def test_waiting_equals_turnaround_minus_burst(self):
        for res in sch.run_all(self.ps, 3):
            for m in self.summary(res).per_process:
                self.assertEqual(m.waiting, m.turnaround - m.burst)
                self.assertLessEqual(m.response, m.waiting)

    def test_fairness_bounds_and_rr_is_fairest(self):
        sums = [self.summary(r) for r in sch.run_all(self.ps, 3)]
        for s in sums:
            self.assertTrue(1 / 6 <= s.fairness <= 1)
        self.assertEqual(max(sums, key=lambda s: s.fairness).algorithm, "Round Robin (q=3)")

    def test_alarm_served_best_by_preemptive_priority(self):
        sums = [self.summary(r) for r in sch.run_all(self.ps, 3)]
        best = metrics.compare(sums, "P4")["alarme_mais_eficiente"]
        self.assertTrue(best.startswith("Prioridade (preemptiva)"))

    def test_jain_index(self):
        self.assertAlmostEqual(metrics.jain_index([1, 1, 1, 1]), 1.0)
        self.assertAlmostEqual(metrics.jain_index([1, 0, 0, 0]), 0.25)


if __name__ == "__main__":
    unittest.main()
