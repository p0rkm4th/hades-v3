import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import gpu_trial_firewall as firewall


class FirewallRuleConstructionTests(unittest.TestCase):
    def test_cp71_uses_checkpoint_scoped_chain_names(self):
        self.assertEqual(firewall.chain_names("CP71"), ("H3CP71FWD", "H3CP71IN"))

    def test_cp71_guard_only_allows_fixed_upstream_port_then_drops_adapter_egress(self):
        calls = []

        def record(*args, **kwargs):
            calls.append(args)
            return type("Result", (), {"returncode": 0})()

        with patch.object(firewall, "exists", side_effect=lambda chain: chain == "DOCKER-USER"), \
                patch.object(firewall, "run", side_effect=record):
            firewall.install("198.51.100.5", "192.0.2.9", 11434, *firewall.chain_names("CP71"))

        self.assertIn(("-A", "H3CP71FWD", "-d", "192.0.2.9/32", "-p", "tcp", "--dport", "11434", "-j", "ACCEPT"), calls)
        self.assertIn(("-A", "H3CP71FWD", "-s", "198.51.100.5/32", "-j", "DROP"), calls)
        self.assertIn(("-A", "H3CP71IN", "-s", "198.51.100.5/32", "-j", "DROP"), calls)
        self.assertIn(("-I", "DOCKER-USER", "1", "-s", "198.51.100.5/32", "-j", "H3CP71FWD"), calls)
        self.assertIn(("-I", "INPUT", "1", "-s", "198.51.100.5/32", "-j", "H3CP71IN"), calls)
        allow_index = calls.index(("-A", "H3CP71FWD", "-d", "192.0.2.9/32", "-p", "tcp", "--dport", "11434", "-j", "ACCEPT"))
        drop_index = calls.index(("-A", "H3CP71FWD", "-s", "198.51.100.5/32", "-j", "DROP"))
        self.assertLess(allow_index, drop_index)


if __name__ == "__main__":
    unittest.main()
