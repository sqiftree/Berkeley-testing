import math
import threading
import unittest
from app import Coordinator
from berkeley import VirtualClock, calculate
from node import NodeServer, rpc


class MathTests(unittest.TestCase):
    def test_example_includes_coordinator(self):
        average, corrections, included = calculate({"A": 20, "B": -10, "C": 35})
        self.assertEqual(average, 11.25)
        self.assertEqual(corrections, {"A": -8.75, "B": 21.25, "C": -23.75})
        self.assertEqual(len(included), 3)

    def test_outlier_is_corrected_but_not_averaged(self):
        average, corrections, included = calculate({"A": 20, "B": -10, "C": 300})
        self.assertAlmostEqual(average, 10 / 3)
        self.assertNotIn("C", included)
        self.assertAlmostEqual(corrections["C"], 10 / 3 - 300)

    def test_all_outliers_and_invalid_values(self):
        self.assertEqual(calculate({"A": 300})[0], 0)
        for value in (math.nan, math.inf):
            with self.assertRaises(ValueError):
                calculate({"A": value})

    def test_virtual_adjustment(self):
        clock = VirtualClock()
        before = clock.now()
        clock.adjust(-20)
        self.assertAlmostEqual(clock.now() - before, -20, delta=.05)


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.servers = []
        for offset in (20, -10, 35):
            server = NodeServer(("127.0.0.1", 0), offset)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.servers.append(server)
        self.coordinator = Coordinator([s.server_address for s in self.servers])

    def tearDown(self):
        for server in self.servers:
            server.shutdown()
            server.server_close()

    def test_real_tcp_converges_and_repeats(self):
        result = self.coordinator.synchronize()
        self.assertAlmostEqual(result["average"], 11.25, delta=.05)
        self.assertTrue(all(n["applied"] for n in result["nodes"]))
        self.assertTrue(all(abs(n["offset"]) < .05 for n in self.coordinator.sample()))
        self.assertAlmostEqual(self.coordinator.synchronize()["average"], 0, delta=.05)

    def test_offline_and_outlier(self):
        self.coordinator.reset("outlier")
        self.servers[1].shutdown()
        self.servers[1].server_close()
        result = self.coordinator.synchronize()
        self.assertAlmostEqual(result["average"], 10, delta=.05)
        self.assertFalse(result["nodes"][1]["online"])
        self.assertFalse(result["nodes"][2]["included"])
        self.assertTrue(result["nodes"][2]["applied"])

    def test_invalid_rpc_and_no_clients(self):
        with self.assertRaises(ValueError):
            rpc(*self.servers[0].server_address, {"action": "adjust", "value": "nan"})
        with self.assertRaises(ValueError):
            Coordinator([]).synchronize()


if __name__ == "__main__":
    unittest.main()
