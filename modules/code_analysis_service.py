
"""Python service used by the Jac CodeAnalyzer walker."""

from modules.source_parser import analyze_python_repository


def analyze_and_query_repository(
    repository_path: str,
    max_files: int = 1000,
    query_symbol: str = "",
    relationship_type: str = "",
) -> dict:
    """Analyze a repository, flatten relationships, and apply query filters."""
    analysis = analyze_python_repository(repository_path, max_files)

    all_relationships = []
    function_count = 0
    class_count = 0

    for file_result in analysis.get("files", []):
        function_count += len(file_result.get("functions", []))
        class_count += len(file_result.get("classes", []))

        for relationship in file_result.get("relationships", []):
            all_relationships.append(
                {
                    "file_path": file_result["file_path"],
                    "type": relationship["type"],
                    "source": relationship["source"],
                    "target": relationship["target"],
                    "line": relationship["line"],
                }
            )

    symbol = query_symbol.strip().casefold()
    requested_type = relationship_type.strip().casefold()

    matching_relationships = [
        relationship
        for relationship in all_relationships
        if (
            not symbol
            or symbol in str(relationship["source"]).casefold()
            or symbol in str(relationship["target"]).casefold()
        )
        and (
            not requested_type
            or str(relationship["type"]).casefold() == requested_type
        )
    ]

    return {
        "status": "success",
        "repository": analysis["repository"],
        "root_path": analysis["root_path"],
        "python_files": analysis["file_count"],
        "valid_python_files": analysis["valid_file_count"],
        "invalid_python_files": analysis["invalid_file_count"],
        "analysis_truncated": analysis["truncated"],
        "functions_discovered": function_count,
        "classes_discovered": class_count,
        "relationships_discovered": len(all_relationships),
        "query": {
            "symbol": query_symbol,
            "relationship_type": relationship_type,
            "matches": len(matching_relationships),
        },
        "relationships": matching_relationships,
    }
