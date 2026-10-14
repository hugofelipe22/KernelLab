import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import devices as dv  # noqa: E402


class TestAccessMatrix(unittest.TestCase):
    def setUp(self):
        self.acl = dv.AccessControlMatrix.load(ROOT / "data" / "access_matrix.json")

    def test_declared_devices_are_allowed(self):
        self.assertTrue(self.acl.allowed("P3", "disco", "use"))
        self.assertTrue(self.acl.allowed("P4", "audio", "use"))
        self.assertTrue(self.acl.allowed("P6", "rede", "use"))

    def test_undeclared_devices_are_denied(self):
        self.assertFalse(self.acl.allowed("P2", "audio", "use"))
        self.assertFalse(self.acl.allowed("P5", "rede", "write"))
        self.assertFalse(self.acl.allowed("P9", "disco", "use"))  # processo desconhecido

    def test_exclusive_only_where_granted(self):
        self.assertTrue(self.acl.allowed("P5", "disco", "exclusive"))
        self.assertFalse(self.acl.allowed("P3", "disco", "exclusive"))

    def test_check_raises(self):
        with self.assertRaises(dv.AccessDenied):
            self.acl.check("P2", "audio", "use")

    def test_invalid_matrix(self):
        with self.assertRaises(ValueError):
            dv.AccessControlMatrix({"P1": {"disco": ["fly"]}}, ["disco"])
        with self.assertRaises(ValueError):
            dv.AccessControlMatrix({"P1": {"gpu": ["use"]}}, ["disco"])


class TestConcurrency(unittest.TestCase):
    def setUp(self):
        self.acl = dv.AccessControlMatrix.load(ROOT / "data" / "access_matrix.json")
        self.reqs = [dv.Request("P3", "write", 0.1, 0.00),
                     dv.Request("P5", "write", 0.1, 0.02, exclusive_ops=2),
                     dv.Request("P6", "read", 0.1, 0.04)]

    def test_mutex_prevents_simultaneous_access(self):
        res = dv.run_scenario(self.acl, "disco", self.reqs, use_mutex=True)
        self.assertEqual(res.max_concurrent, 1)
        self.assertEqual(res.violations, 0)

    def test_without_mutex_overlap_happens(self):
        res = dv.run_scenario(self.acl, "disco", self.reqs, use_mutex=False)
        self.assertGreater(res.violations, 0)

    def test_fifo_order_of_service(self):
        res = dv.run_scenario(self.acl, "disco", self.reqs, use_mutex=True)
        used = [e.pid for e in res.events if e.action.startswith("USA")]
        self.assertEqual(used, ["P3", "P5", "P5", "P6"])

    def test_unauthorized_request_denied_and_does_not_block(self):
        reqs = self.reqs + [dv.Request("P4", "write", 0.1, 0.01)]  # P4 não usa disco
        res = dv.run_scenario(self.acl, "disco", reqs, use_mutex=True)
        self.assertEqual(res.denied, ["P4"])
        self.assertEqual(res.violations, 0)

    def test_exclusive_session_requires_permission(self):
        reqs = [dv.Request("P3", "write", 0.05, 0.0, exclusive_ops=1)]  # P3 sem exclusive
        res = dv.run_scenario(self.acl, "disco", reqs)
        self.assertEqual(res.denied, ["P3"])

    def test_release_by_non_owner_fails(self):
        m = dv.FifoMutex()
        m.acquire("A")
        with self.assertRaises(RuntimeError):
            m.release("B")


if __name__ == "__main__":
    unittest.main()
