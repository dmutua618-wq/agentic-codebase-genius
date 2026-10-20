
import tempfile
import unittest
from pathlib import Path

from modules.repository_tools import (
    _validate_github_url,
    generate_file_tree,
    map_repository,
    summarise_readme,
)


class RepoMapperTests(unittest.TestCase):
    def test_maps_files_and_ignores_irrelevant_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            (root / "main.py").write_text(
                "print('hello')",
                encoding="utf-8",
            )

            (root / ".git").mkdir()
            (root / ".git" / "config").write_text(
                "ignored",
                encoding="utf-8",
            )

            (root / ".venv").mkdir()
            (root / ".venv" / "ignored.py").write_text(
                "ignored",
                encoding="utf-8",
            )

            result = generate_file_tree(str(root))
            paths = [item["path"] for item in result["files"]]

            self.assertIn("main.py", paths)
            self.assertFalse(
                any(path.startswith(".git/") for path in paths)
            )
            self.assertFalse(
                any(path.startswith(".venv/") for path in paths)
            )

    def test_rejects_invalid_github_url(self):
        with self.assertRaises(ValueError):
            _validate_github_url(
                "https://example.com/not-a-repository"
            )

    def test_validates_github_repository_url(self):
        owner, repo = _validate_github_url(
            "https://github.com/pallets/flask"
        )

        self.assertEqual(owner, "pallets")
        self.assertEqual(repo, "flask")

    def test_summarises_readme(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            (root / "README.md").write_text(
                "# Example Project\n"
                "A project for testing documentation.\n"
                "## Installation\n"
                "Install the dependencies.\n",
                encoding="utf-8",
            )

            result = summarise_readme(str(root))

            self.assertEqual(result["title"], "Example Project")
            self.assertIn("Installation", result["headings"])
            self.assertIn(
                "testing documentation",
                result["summary"],
            )

    def test_handles_missing_readme(self):
        with tempfile.TemporaryDirectory() as temp:
            result = summarise_readme(temp)

            self.assertIsNone(result["readme_path"])
            self.assertEqual(result["headings"], [])

    def test_combines_repository_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            (root / "main.py").write_text(
                "print('hello')",
                encoding="utf-8",
            )

            (root / "README.md").write_text(
                "# Demo\nA small project.",
                encoding="utf-8",
            )

            result = map_repository(str(root))

            self.assertEqual(result["repository"], root.name)
            self.assertEqual(result["file_tree"]["file_count"], 2)
            self.assertEqual(
                result["language_file_counts"][".py"],
                1,
            )


if __name__ == "__main__":
    unittest.main()
