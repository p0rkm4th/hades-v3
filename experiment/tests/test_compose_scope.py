import unittest
from unittest.mock import patch

from compose_scope import compose_command, compose_project


class ComposeProjectScopeTests(unittest.TestCase):
    def test_requires_explicit_disposable_project_name(self):
        for value in (None, "", "hades-v3-lab", "cp69offline", "hades-v3-exp-bad_name", "hades-v3-exp-Upper"):
            with self.subTest(value=value), self.assertRaises(SystemExit):
                compose_project(value)

    def test_accepts_scoped_project_and_inserts_explicit_compose_flag(self):
        self.assertEqual(compose_project("hades-v3-exp-family6-cp72-a1"),
                         "hades-v3-exp-family6-cp72-a1")
        with patch.dict("os.environ", {"HADES_COMPOSE_PROJECT": "hades-v3-exp-family8-cp72-c1"}):
            self.assertEqual(compose_command("experiment/compose.yaml"), [
                "docker", "compose", "-p", "hades-v3-exp-family8-cp72-c1",
                "-f", "experiment/compose.yaml",
            ])


if __name__ == "__main__":
    unittest.main()
