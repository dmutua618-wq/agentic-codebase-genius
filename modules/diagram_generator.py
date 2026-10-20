
"""Generate focused Mermaid architecture diagrams from source analysis."""

from __future__ import annotations

import re
from pathlib import PurePosixPath


IGNORED_CALLS = {
    "append", "clear", "copy", "count", "extend", "format",
    "get", "index", "insert", "items", "join", "keys", "len",
    "pop", "replace", "setdefault", "sort", "split", "strip",
    "update", "values",
}


def _short_name(name: str) -> str:
    """Return the last component of a qualified symbol name."""
    return name.rsplit(".", 1)[-1].strip()


def _safe_label(label: str) -> str:
    """Escape potentially problematic Mermaid label characters."""
    label = label.replace("&", "&amp;")
    label = label.replace('"', "'")
    label = label.replace("<", "&lt;")
    label = label.replace(">", "&gt;")
    return re.sub(r"[\r\n]+", " ", label)


def _is_test_file(file_path: str) -> bool:
    """Identify test files and test directories."""
    normalized = file_path.replace("\\", "/").strip("/")
    path = PurePosixPath(normalized)
    parts = {part.lower() for part in path.parts}
    filename = path.name.lower()

    return (
        "tests" in parts
        or "test" in parts
        or filename.startswith("test_")
        or filename.endswith("_test.py")
    )


def _collect_defined_symbols(
    files: list[dict],
) -> tuple[set[str], set[str]]:
    """Collect application function, method, and class names."""
    functions: set[str] = set()
    classes: set[str] = set()

    for file_result in files:
        if not file_result.get("valid", False):
            continue

        if _is_test_file(file_result.get("file_path", "")):
            continue

        for function in file_result.get("functions", []):
            name = function.get("name")
            if name:
                functions.add(_short_name(name))

        for class_info in file_result.get("classes", []):
            class_name = class_info.get("name")
            if class_name:
                classes.add(_short_name(class_name))

            for method in class_info.get("methods", []):
                method_name = method.get("name")
                if method_name:
                    functions.add(_short_name(method_name))

    return functions, classes


def _test_symbol(name: str) -> bool:
    """Identify test functions and test classes by common naming patterns."""
    parts = name.replace("::", ".").split(".")

    for part in parts:
        lowered = part.lower()

        if lowered.startswith("test_") or lowered.endswith("_test"):
            return True

        if lowered.startswith("test") and len(lowered) > 4:
            if lowered[4].isupper() or lowered[4] == "_":
                return True

    return False


def generate_mermaid_diagram(
    analysis: dict,
    max_relationships: int = 60,
) -> str:
    """Generate a Mermaid diagram of application code relationships."""
    if max_relationships < 1:
        raise ValueError("max_relationships must be greater than zero.")

    files = analysis.get("files", [])
    relationships = analysis.get("relationships", [])

    production_files = [
        item
        for item in files
        if not _is_test_file(item.get("file_path", ""))
    ]

    defined_functions, defined_classes = _collect_defined_symbols(
        production_files
    )
    has_symbol_information = bool(defined_functions or defined_classes)

    selected = []
    seen_edges = set()

    for relationship in relationships:
        source = str(relationship.get("source", "")).strip()
        target = str(relationship.get("target", "")).strip()
        relation_type = str(relationship.get("type", "")).strip().lower()

        if not source or not target:
            continue

        # Never include a relationship originating in a test function.
        if _test_symbol(source):
            continue

        # Test functions should not appear as targets either.
        if _test_symbol(target):
            continue

        source_short = _short_name(source)
        target_short = _short_name(target)

        if relation_type == "call":
            if target_short in IGNORED_CALLS:
                continue

            if (
                has_symbol_information
                and target_short not in defined_functions
            ):
                continue

        elif relation_type == "inheritance":
            if has_symbol_information and (
                source_short not in defined_classes
                or target_short not in defined_classes
            ):
                continue
        else:
            continue

        edge = (source, target, relation_type)

        if edge in seen_edges:
            continue

        seen_edges.add(edge)
        selected.append({
            "source": source,
            "target": target,
            "type": relation_type,
        })

    was_truncated = len(selected) > max_relationships
    selected = selected[:max_relationships]

    lines = [
        "flowchart TD",
        '    START["Application architecture"]',
    ]

    node_ids: dict[str, str] = {}
    next_id = 0

    def node_id(label: str) -> str:
        nonlocal next_id

        if label not in node_ids:
            identifier = f"N{next_id}"
            next_id += 1
            node_ids[label] = identifier
            lines.append(f'    {identifier}["{_safe_label(label)}"]')

        return node_ids[label]

    rendered_edges = []

    for relationship in selected:
        source_id = node_id(relationship["source"])
        target_id = node_id(relationship["target"])

        if relationship["type"] == "inheritance":
            # The analyzer records base class as source and derived class
            # as target.
            rendered_edges.append(
                f"    {target_id} -->|inherits| {source_id}"
            )
        else:
            rendered_edges.append(
                f"    {source_id} -->|calls| {target_id}"
            )

    if rendered_edges:
        lines.extend(rendered_edges)
    else:
        lines.append(
            '    START --> INFO["No significant application relationships detected"]'
        )

    if was_truncated:
        lines.append(
            f'    NOTE["Diagram limited to {max_relationships} relationships"]'
        )

    return "\n".join(lines) + "\n"
