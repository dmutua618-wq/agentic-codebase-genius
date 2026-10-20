
"""Generate Markdown documentation and Mermaid architecture diagrams."""

from pathlib import Path

from modules.diagram_generator import (
    _is_test_file,
    generate_mermaid_diagram,
)
from modules.repository_tools import map_repository
from modules.source_parser import analyze_python_repository


def _format_list(
    items: list[str],
    empty_message: str = "None detected.",
) -> str:
    """Format values as Markdown bullets."""
    if not items:
        return f"- {empty_message}"

    return "\n".join(f"- `{item}`" for item in items)


def _format_parameters(parameters: list[str]) -> str:
    """Format a function's parameters."""
    return ", ".join(parameters)


def _collect_relationships(analysis: dict) -> list[dict]:
    """Collect relationships from non-test Python files."""
    relationships = []

    for file_result in analysis.get("files", []):
        if _is_test_file(file_result.get("file_path", "")):
            continue

        relationships.extend(file_result.get("relationships", []))

    return relationships


def _generate_api_reference(analysis: dict) -> str:
    """Generate an API reference for analyzed application source files."""
    sections = []

    for file_result in analysis.get("files", []):
        if not file_result.get("valid", False):
            continue

        if _is_test_file(file_result.get("file_path", "")):
            continue

        file_path = file_result.get("file_path", "unknown.py")
        sections.append(f"### `{file_path}`")

        imports = file_result.get("imports", [])
        if imports:
            sections.append("**Imports**")
            sections.append(_format_list(imports))
            sections.append("")

        for class_info in file_result.get("classes", []):
            class_name = class_info.get("name", "UnknownClass")
            bases = class_info.get("bases", [])

            if bases:
                base_text = ", ".join(f"`{base}`" for base in bases)
                sections.append(f"- `class {class_name}({base_text})`")
            else:
                sections.append(f"- `class {class_name}`")

            if class_info.get("docstring"):
                sections.append(f"  - {class_info['docstring']}")

            for method in class_info.get("methods", []):
                prefix = "async " if method.get("is_async") else ""
                name = method.get("name", "unknown_method")
                parameters = _format_parameters(
                    method.get("parameters", [])
                )
                sections.append(
                    f"  - `{prefix}def {name}({parameters})`"
                )

                if method.get("docstring"):
                    sections.append(f"    - {method['docstring']}")

        functions = file_result.get("functions", [])

        if functions:
            sections.append("")
            sections.append("**Functions**")

            for function in functions:
                prefix = "async " if function.get("is_async") else ""
                name = function.get("name", "unknown_function")
                parameters = _format_parameters(
                    function.get("parameters", [])
                )
                sections.append(
                    f"- `{prefix}def {name}({parameters})`"
                )

                if function.get("docstring"):
                    sections.append(f"  - {function['docstring']}")

        sections.append("")

    if not sections:
        return "No application Python API definitions were detected."

    return "\n".join(sections)


def _generate_installation_section(mapped: dict) -> str:
    """Infer basic setup guidance from root-level files."""
    root_files = {
        Path(item["path"]).name.lower()
        for item in mapped.get("file_tree", {}).get("files", [])
        if "/" not in item["path"].replace("\\", "/")
    }

    steps = [
        "1. Install a compatible Python version.",
        "2. Create and activate a virtual environment.",
        "3. Install the project's dependencies.",
        "4. Follow the project's documented startup command.",
    ]

    if "requirements.txt" in root_files:
        steps[2] = (
            "3. Install dependencies using "
            "`python -m pip install -r requirements.txt`."
        )
    elif "pyproject.toml" in root_files:
        steps[2] = (
            "3. Install the project with `python -m pip install .`, "
            "if supported by its configuration."
        )
    elif "pipfile" in root_files:
        steps[2] = "3. Install dependencies using Pipenv."

    if "main.py" in root_files:
        steps[3] = "4. Start the application using `python main.py`."
    elif "app.py" in root_files:
        steps[3] = "4. Start the application using `python app.py`."

    return "\n".join(steps)


def generate_documentation(
    repository_root: str,
    output_root: str = "outputs",
    max_python_files: int = 1000,
) -> dict:
    """Analyze a repository and write documentation artifacts."""
    root = Path(repository_root).resolve()
    destination_root = Path(output_root).resolve()

    if not root.exists():
        raise FileNotFoundError(
            f"Repository path does not exist: {root}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Repository path is not a directory: {root}"
        )

    if max_python_files < 1:
        raise ValueError("max_python_files must be greater than zero.")

    mapped = map_repository(str(root))
    analysis = analyze_python_repository(
        str(root),
        max_files=max_python_files,
    )

    relationships = _collect_relationships(analysis)

    application_files = [
        item
        for item in analysis.get("files", [])
        if not _is_test_file(item.get("file_path", ""))
    ]

    diagram = generate_mermaid_diagram({
        "relationships": relationships,
        "files": application_files,
    })

    repository_name = mapped.get("repository", root.name)
    output_dir = destination_root / repository_name
    output_dir.mkdir(parents=True, exist_ok=True)

    docs_path = output_dir / "docs.md"
    diagram_path = output_dir / "architecture.mmd"

    file_tree = mapped.get("file_tree", {})
    readme = mapped.get("readme", {})
    language_counts = mapped.get("language_file_counts", {})

    readme_summary = (
        readme.get("summary", "")
        if isinstance(readme, dict)
        else str(readme or "")
    )

    if not readme_summary.strip():
        readme_summary = (
            "No README summary was available. Review the repository "
            "source files and configuration for more information."
        )

    extension_lines = [
        f"- `{extension or '[no extension]'}`: {count} file(s)"
        for extension, count in sorted(language_counts.items())
    ]

    if not extension_lines:
        extension_lines = ["- No file-extension statistics available."]

    valid_files = [
        item.get("file_path", "")
        for item in analysis.get("files", [])
        if item.get("valid", False)
    ]

    invalid_files = [
        item
        for item in analysis.get("files", [])
        if not item.get("valid", False)
    ]

    valid_results = [
        item
        for item in analysis.get("files", [])
        if item.get("valid", False)
    ]

    function_count = sum(
        len(item.get("functions", []))
        for item in valid_results
    )

    class_count = sum(
        len(item.get("classes", []))
        for item in valid_results
    )

    method_count = sum(
        len(class_info.get("methods", []))
        for item in valid_results
        for class_info in item.get("classes", [])
    )

    api_reference = _generate_api_reference(analysis)
    installation = _generate_installation_section(mapped)

    docs = f"""# {repository_name}

## 1. Project Overview

Generated by **Codebase Genius**, an agentic code-documentation system.

**Repository location:** `{root}`

### README Summary

{readme_summary}

## 2. Repository Statistics

| Metric | Value |
|---|---:|
| Total files discovered | {file_tree.get("file_count", 0)} |
| Python files analyzed | {analysis.get("file_count", 0)} |
| Valid Python files | {analysis.get("valid_file_count", 0)} |
| Python files with syntax errors | {analysis.get("invalid_file_count", 0)} |
| Functions discovered | {function_count} |
| Classes discovered | {class_count} |
| Class methods discovered | {method_count} |
| Application code relationships | {len(relationships)} |

## 3. File Types

{chr(10).join(extension_lines)}

## 4. Installation and Execution

These are inferred suggestions. Confirm the steps against the
repository's own instructions before running the project.

{installation}

## 5. Python API Reference

{api_reference}

## 6. Application Architecture

The Mermaid diagram is also saved separately as `architecture.mmd`.
Test files are excluded from the application architecture diagram.

```mermaid
{diagram.rstrip()}
```

## 7. Python File Inventory

{_format_list(valid_files, "No valid Python files were analyzed.")}

## 8. Analysis Warnings

"""

    if invalid_files:
        for item in invalid_files:
            docs += (
                f"- `{item.get('file_path', 'unknown')}`: "
                f"{item.get('error', 'Could not parse this file.')}\n"
            )
    else:
        docs += "- No Python syntax errors were reported.\n"

    if analysis.get("truncated", False):
        docs += (
            "- Analysis reached the configured Python file limit. "
            "Increase `max_python_files` to inspect more files.\n"
        )

    if file_tree.get("truncated", False):
        docs += "- The repository file inventory was truncated.\n"

    docs += """
## 9. Limitations

- This documentation is generated using static source analysis.
- Runtime behavior and external services are not automatically verified.
- Dynamic calls may not appear in the architecture diagram.
- Installation guidance is inferred and should be verified.
- Review the generated documentation before publishing it.

---

*Generated by Codebase Genius.*
"""

    docs_path.write_text(docs, encoding="utf-8")
    diagram_path.write_text(diagram, encoding="utf-8")

    return {
        "status": "success",
        "repository": repository_name,
        "root_path": str(root),
        "output_directory": str(output_dir),
        "documentation_path": str(docs_path),
        "diagram_path": str(diagram_path),
        "python_files_analyzed": analysis.get("file_count", 0),
        "valid_python_files": analysis.get("valid_file_count", 0),
        "invalid_python_files": analysis.get("invalid_file_count", 0),
        "functions_discovered": function_count,
        "classes_discovered": class_count,
        "methods_discovered": method_count,
        "relationships_discovered": len(relationships),
        "analysis_truncated": analysis.get("truncated", False),
    }
