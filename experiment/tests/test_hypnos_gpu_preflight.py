import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.hypnos_gpu_preflight import (EXPECTED_DIGEST, inspect_payload,
                                          parse_environment, validate_runtime_config)


class HypnosPreflightTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.unit = {"ActiveState": "active", "SubState": "running", "UnitFileState": "enabled",
                     "Environment": 'OLLAMA_HOST=ollama-hypnos.invalid:11434 OLLAMA_CONTEXT_LENGTH=65536'}
        self.responses = {
            "/api/version": {"version": "0.31.1"},
            "/api/tags": {"models": [{"name": "gemma4:12b", "digest": EXPECTED_DIGEST}]},
            "/api/ps": {"models": []},
            "/api/show": {"details": {"quantization_level": "Q4_K_M"}},
        }

    def api(self, path, body=None):
        self.calls.append((path, body))
        return self.responses[path]

    def test_cp70_false_negative_uses_scotty_user_service_binding_and_accepts_unloaded(self):
        result = inspect_payload(self.unit, self.api)
        self.assertEqual(result["service"], "healthy")
        self.assertEqual(result["listener"], "available")
        self.assertEqual(result["model"], "installed_but_unloaded")
        self.assertIsNone(result["effective_context"])
        self.assertEqual(result["context_status"], "requires_bounded_probe")
        self.assertEqual(result["configured_base"], "http://ollama-hypnos.invalid:11434")
        self.assertEqual([path for path, _ in self.calls],
                         ["/api/version", "/api/tags", "/api/ps", "/api/show"])

    def test_inactive_system_service_does_not_override_actual_user_service(self):
        # CP70's system-scope ollama.service was absent; only the actual scotty
        # user unit is authoritative for this endpoint.
        result = inspect_payload(self.unit, self.api)
        self.assertEqual(result["service"], "healthy")

    def test_unhealthy_actual_user_unit_is_rejected(self):
        self.unit["ActiveState"] = "inactive"
        with self.assertRaisesRegex(RuntimeError, "ActiveState"):
            inspect_payload(self.unit, self.api)

    def test_digest_drift_is_rejected(self):
        self.responses["/api/tags"]["models"][0]["digest"] = "wrong"
        with self.assertRaisesRegex(RuntimeError, "digest"):
            inspect_payload(self.unit, self.api)

    def test_api_version_drift_is_rejected(self):
        self.responses["/api/version"]["version"] = "future-version"
        with self.assertRaisesRegex(RuntimeError, "API version"):
            inspect_payload(self.unit, self.api)

    def test_listener_port_drift_is_rejected(self):
        self.unit["Environment"] = "OLLAMA_HOST=ollama-hypnos.invalid:11437"
        with self.assertRaisesRegex(RuntimeError, "port"):
            inspect_payload(self.unit, self.api)

    def test_wildcard_listener_is_not_used_as_probe_destination(self):
        self.unit["Environment"] = "OLLAMA_HOST=0.0.0.0:11434"
        with self.assertRaisesRegex(ValueError, "wildcard"):
            inspect_payload(self.unit, self.api)

    def test_resident_wrong_context_is_reported_without_calling_it_verified(self):
        self.responses["/api/ps"] = {"models": [{"name": "gemma4:12b", "context_length": 32768}]}
        result = inspect_payload(self.unit, self.api)
        self.assertEqual(result["model"], "loaded")
        self.assertEqual(result["context_status"], "mismatch")

    def test_systemd_environment_parser_handles_quoted_values(self):
        parsed = parse_environment('OLLAMA_HOST="ollama-hypnos.invalid:11434" OLLAMA_CONTEXT_LENGTH=65536')
        self.assertEqual(parsed["OLLAMA_HOST"], "ollama-hypnos.invalid:11434")
        self.assertEqual(parsed["OLLAMA_CONTEXT_LENGTH"], "65536")

    def test_supervised_and_live_runtime_configuration_must_match(self):
        approved = {"OLLAMA_HOST": "ollama-hypnos.invalid:11434", "OLLAMA_MODELS": "/models",
                    "OLLAMA_CONTEXT_LENGTH": "65536", "OLLAMA_NUM_PARALLEL": "1",
                    "OLLAMA_MAX_LOADED_MODELS": "1", "CUDA_VISIBLE_DEVICES": "0,1",
                    "OLLAMA_LLM_LIBRARY": "cuda_v12", "OLLAMA_KEEP_ALIVE": "30m"}
        validate_runtime_config(approved, dict(approved), "scotty", True)
        with self.assertRaisesRegex(RuntimeError, "drift"):
            validate_runtime_config(approved, {**approved, "OLLAMA_CONTEXT_LENGTH": "32768"}, "scotty", True)
        with self.assertRaisesRegex(RuntimeError, "owner"):
            validate_runtime_config(approved, approved, "root", True)
        with self.assertRaisesRegex(RuntimeError, "NVIDIA"):
            validate_runtime_config(approved, approved, "scotty", False)


if __name__ == "__main__":
    unittest.main()
