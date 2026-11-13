import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "docs", Path(__file__).resolve().parents[1] / "scripts/docs.py"
)
docs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(docs)


class DocsTest(unittest.TestCase):
    def test_repository_sources(self):
        with patch.dict(os.environ, {"REPOSITORY": "fork/project", "GITHUB_REPOSITORY": "other/project"}, clear=True):
            self.assertEqual(docs.repository_slug(), "fork/project")
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "other/project"}, clear=True):
            self.assertEqual(docs.repository_slug(), "other/project")
        with patch.dict(os.environ, {}, clear=True):
            for origin in ("https://github.com/owner/repo.git", "git@github.com:owner/repo.git", "ssh://git@github.com/owner/repo.git", "https://github.com/owner/repo"):
                with self.subTest(origin=origin), patch.object(docs.subprocess, "check_output", return_value=origin):
                    self.assertEqual(docs.repository_slug(), "owner/repo")
            with patch.object(docs.subprocess, "check_output", return_value="https://example.org/owner/repo"):
                with self.assertRaises(ValueError):
                    docs.repository_slug()

    def test_config_rendered_separately_and_removed(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(docs, "ROOT", Path(directory)):
            config = Path(directory) / "zensical.toml"
            config.write_text('[project]\nrepo_url = "https://github.com/{repository}"\n')
            original = config.read_bytes()
            with self.assertRaises(RuntimeError):
                with docs.prepared_config("fork/project") as rendered:
                    self.assertNotEqual(rendered, config)
                    self.assertIn("https://github.com/fork/project", rendered.read_text())
                    self.assertEqual(config.read_bytes(), original)
                    raise RuntimeError("build failed")
            self.assertFalse(rendered.exists())
            self.assertEqual(config.read_bytes(), original)

    def test_build_and_preview_share_preprocessing(self):
        for command in ("build", "serve"):
            with patch.object(docs.sys, "argv", ["docs.py", command, "--strict"]), patch.object(docs, "repository_slug", return_value="fork/project"), patch.object(docs, "prepared_config") as prepare, patch.object(docs.subprocess, "call", return_value=0) as run:
                self.assertEqual(docs.main(), 0)
                prepare.assert_called_once_with("fork/project")
                run.assert_called_once_with([docs.sys.executable, "-m", "zensical", command, "-f", str(prepare.return_value.__enter__.return_value), "--strict"], cwd=docs.ROOT)
