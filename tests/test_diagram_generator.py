
"""Unit tests for Mermaid architecture diagram generation."""

import unittest

from modules.diagram_generator import generate_mermaid_diagram


class TestDiagramGenerator(unittest.TestCase):
    def setUp(self):
        self.analysis = {
            "files": [
                {
                    "file_path": "modules/service.py",
                    "valid": True,
                    "functions": [
                        {"name": "start_service"},
                        {"name": "load_config"},
                    ],
                    "classes": [
                        {
                            "name": "BaseService",
                            "bases": [],
                            "methods": [],
                        },
                        {
                            "name": "UserService",
                            "bases": ["BaseService"],
                            "methods": [{"name": "get_user"}],
                        },
                    ],
                },
                {
                    "file_path": "tests/test_service.py",
                    "valid": True,
                    "functions": [{"name": "test_start_service"}],
                    "classes": [],
                },
            ],
            "relationships": [
                {
                    "source": "start_service",
                    "target": "load_config",
                    "type": "call",
                },
                {
                    "source": "start_service",
                    "target": "load_config",
                    "type": "call",
                },
                {
                    "source": "start_service",
                    "target": "append",
                    "type": "call",
                },
                {
                    "source": "test_start_service",
                    "target": "start_service",
                    "type": "call",
                },
                {
                    "source": "BaseService",
                    "target": "UserService",
                    "type": "inheritance",
                },
            ],
        }

    def test_generates_mermaid_flowchart(self):
        diagram = generate_mermaid_diagram(self.analysis)

        self.assertIn("flowchart TD", diagram)
        self.assertIn("Application architecture", diagram)

    def test_keeps_project_function_calls(self):
        diagram = generate_mermaid_diagram(self.analysis)

        self.assertIn('["start_service"]', diagram)
        self.assertIn('["load_config"]', diagram)
        self.assertIn("|calls|", diagram)

    def test_removes_duplicate_relationships(self):
        diagram = generate_mermaid_diagram(self.analysis)

        # Only one application call should remain after filtering
        # duplicate calls, test-only calls, and utility calls.
        self.assertEqual(diagram.count("|calls|"), 1)

    def test_ignores_common_utility_calls(self):
        diagram = generate_mermaid_diagram(self.analysis)

        self.assertNotIn('["append"]', diagram)

    def test_excludes_test_only_functions(self):
        diagram = generate_mermaid_diagram(self.analysis)

        self.assertNotIn("test_start_service", diagram)

    def test_includes_class_inheritance(self):
        diagram = generate_mermaid_diagram(self.analysis)

        self.assertIn('["BaseService"]', diagram)
        self.assertIn('["UserService"]', diagram)
        self.assertIn("|inherits|", diagram)

    def test_limits_number_of_relationships(self):
        analysis = {
            "files": [
                {
                    "file_path": "modules/example.py",
                    "valid": True,
                    "functions": [
                        {"name": "first"},
                        {"name": "second"},
                        {"name": "third"},
                    ],
                    "classes": [],
                }
            ],
            "relationships": [
                {
                    "source": "first",
                    "target": "second",
                    "type": "call",
                },
                {
                    "source": "second",
                    "target": "third",
                    "type": "call",
                },
            ],
        }

        diagram = generate_mermaid_diagram(
            analysis,
            max_relationships=1,
        )

        self.assertIn("Diagram limited to 1 relationships", diagram)
        self.assertEqual(diagram.count("|calls|"), 1)

    def test_rejects_zero_relationship_limit(self):
        with self.assertRaises(ValueError):
            generate_mermaid_diagram(
                self.analysis,
                max_relationships=0,
            )

    def test_handles_no_relationships(self):
        diagram = generate_mermaid_diagram({
            "files": [],
            "relationships": [],
        })

        self.assertIn(
            "No significant application relationships",
            diagram,
        )


if __name__ == "__main__":
    unittest.main()
