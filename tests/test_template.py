import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


init = load_script("init_workspace")
check = load_script("check_template")


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.target = self.base / "new-family"

    def test_empty_private_workspace_has_no_sample_learning_history(self):
        init.create_workspace(self.target)
        self.assertTrue((self.target / "AGENTS.md").exists())
        self.assertTrue((self.target / "materials").is_dir())
        self.assertIn("未知", (self.target / "knowledge-base/reports/latest.md").read_text())
        self.assertIn("待填写", (self.target / "knowledge-base/student-profile.md").read_text())
        self.assertFalse((self.target / "examples").exists())
        self.assertFalse((self.target / ".git").exists())
        self.assertEqual((self.target / ".gitignore").read_text().splitlines()[-1], "*")
        links = [str(path.relative_to(self.target)) for path in self.target.rglob("*.md")]
        self.assertEqual(check.check_files(self.target, links), [])

    def test_accepts_existing_empty_directory(self):
        self.target.mkdir()
        init.create_workspace(self.target)
        self.assertTrue((self.target / "README.md").is_file())

    def test_rejects_nonempty_directory_and_preserves_data(self):
        self.target.mkdir()
        original = self.target / "notes.txt"
        original.write_text("private learning notes")
        with self.assertRaises(ValueError):
            init.create_workspace(self.target)
        self.assertEqual(original.read_text(), "private learning notes")
        self.assertEqual(list(self.target.iterdir()), [original])

    def test_rejects_a_file_target(self):
        self.target.write_text("keep")
        with self.assertRaises(ValueError):
            init.create_workspace(self.target)
        self.assertEqual(self.target.read_text(), "keep")

    def test_rejects_public_template_and_its_descendant(self):
        for target in (ROOT, ROOT / "private-child"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                init.create_workspace(target)

    def test_rejects_symlink_target_without_touching_destination(self):
        actual = self.base / "actual"
        actual.mkdir()
        self.target.symlink_to(actual, target_is_directory=True)
        with self.assertRaises(ValueError):
            init.create_workspace(self.target)
        self.assertEqual(list(actual.iterdir()), [])

    def test_missing_template_fails_before_creating_target(self):
        source = self.base / "missing-template"
        source.mkdir()
        with self.assertRaises(ValueError):
            init.create_workspace(self.target, source)
        self.assertFalse(self.target.exists())

    def test_source_symlink_is_not_copied(self):
        source = self.base / "linked-template"
        source.mkdir()
        (source / "AGENTS.md").symlink_to(ROOT / "AGENTS.md")
        with self.assertRaises(ValueError):
            init.create_workspace(self.target, source)
        self.assertFalse(self.target.exists())

    def test_default_gitignore_covers_nested_learning_data(self):
        init.create_workspace(self.target)
        subprocess.run(["git", "init", "--quiet", str(self.target)], check=True)
        result = subprocess.run(
            ["git", "check-ignore", "knowledge-base/student-profile.md", "materials/photo.jpeg"],
            cwd=self.target, capture_output=True, text=True, check=True,
        )
        self.assertEqual(len(result.stdout.splitlines()), 2)


class PublishChecks(unittest.TestCase):
    def test_allowlist_contains_only_shipped_generic_files(self):
        self.assertEqual(len(init.TEMPLATE_FILES), len(set(init.TEMPLATE_FILES)))
        self.assertEqual(check.check_files(ROOT, list(init.TEMPLATE_FILES)), [])

    def test_link_and_known_private_path_are_rejected_without_echoing_value(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "README.md").write_text("[missing](missing.md)\n/U" + "sers/example/private.txt")
            errors = check.check_files(root, ["README.md"])
            self.assertEqual(len(errors), 2)
            self.assertNotIn("example", "\n".join(errors))

    def test_unapproved_binary_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "audio.wav").write_bytes(b"\xff\xfe")
            self.assertTrue(check.check_files(root, ["audio.wav"]))


if __name__ == "__main__":
    unittest.main()
