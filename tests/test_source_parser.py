
import tempfile
import unittest
from pathlib import Path

from modules.source_parser import (
    analyze_python_file,
    analyze_python_repository,
    analyze_source,
)


class TestAnalyzeSource(unittest.TestCase):
    def test_extracts_imports_functions_and_parameters(self):
        source = """
import json
from pathlib import Path

def load_data(path, *, encoding="utf-8"):
    return Path(path).read_text(encoding=encoding)
"""
        result = analyze_source(source, "example.py")

        self.assertTrue(result["valid"])
        self.assertEqual(len(result["imports"]), 2)
        self.assertEqual(result["functions"][0]["name"], "load_data")
        self.assertEqual(
            result["functions"][0]["parameters"],
            ["path", "encoding"],
        )
        self.assertIn(
            "Path.read_text",
            result["functions"][0]["calls"],
        )

    def test_detects_class_inheritance_and_methods(self):
        source = """
class Parent:
    def speak(self):
        return "hello"

class Child(Parent):
    def greet(self):
        return self.speak()
"""
        result = analyze_source(source)

        self.assertTrue(result["valid"])
        self.assertEqual(len(result["classes"]), 2)
        self.assertEqual(result["classes"][1]["name"], "Child")
        self.assertEqual(result["classes"][1]["bases"], ["Parent"])
        self.assertEqual(
            result["classes"][1]["methods"][0]["name"],
            "greet",
        )
        self.assertTrue(
            any(
                relation["type"] == "inheritance"
                and relation["source"] == "Child"
                and relation["target"] == "Parent"
                for relation in result["relationships"]
            )
        )

    def test_detects_function_calls(self):
        source = """
def helper():
    return 10

def main():
    return helper()
"""
        result = analyze_source(source)

        self.assertTrue(
            any(
                call["caller"] == "main"
                and call["callee"] == "helper"
                for call in result["calls"]
            )
        )

    def test_reports_syntax_errors_without_crashing(self):
        result = analyze_source("def broken(:", "broken.py")

        self.assertFalse(result["valid"])
        self.assertIsNotNone(result["syntax_error"])
        self.assertEqual(result["syntax_error"]["line"], 1)

    def test_detects_async_functions(self):
        source = """
async def fetch_data(url):
    return url
"""
        result = analyze_source(source)

        self.assertTrue(result["valid"])
        self.assertTrue(result["functions"][0]["async"])


class TestFileAndRepositoryAnalysis(unittest.TestCase):
    def test_analyzes_python_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "sample.py"
            file_path.write_text(
                "def calculate():\n    return 2 + 2\n",
                encoding="utf-8",
            )

            result = analyze_python_file(str(file_path))

            self.assertTrue(result["valid"])
            self.assertEqual(result["file_path"], file_path.as_posix())
            self.assertEqual(result["functions"][0]["name"], "calculate")

    def test_rejects_non_python_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "notes.txt"
            file_path.write_text("hello", encoding="utf-8")

            with self.assertRaises(ValueError):
                analyze_python_file(str(file_path))

    def test_repository_analysis_ignores_virtual_environments(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "app.py").write_text(
                "def run():\n    return True\n",
                encoding="utf-8",
            )

            venv = root / ".venv"
            venv.mkdir()
            (venv / "ignored.py").write_text(
                "def ignored():\n    pass\n",
                encoding="utf-8",
            )

            result = analyze_python_repository(str(root))

            self.assertEqual(result["file_count"], 1)
            self.assertEqual(
                result["files"][0]["file_path"],
                "app.py",
            )
            self.assertFalse(result["truncated"])

    def test_validates_repository_and_file_limit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                analyze_python_repository(temp_dir, max_files=0)

        with self.assertRaises(ValueError):
            analyze_python_repository("this-path-should-not-exist-12345")


if __name__ == "__main__":
    unittest.main()
