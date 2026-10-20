
import ast
from pathlib import Path


IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".idea",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "site-packages",
    ".next",
    "coverage",
}


def _get_name(node: ast.AST) -> str:
    """Convert a name or attribute expression into readable text."""
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = _get_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    if isinstance(node, ast.Call):
        return _get_name(node.func)

    return ""


class _SourceAnalyzer(ast.NodeVisitor):
    """Collect structural information and relationships from Python AST."""

    def __init__(self) -> None:
        self.imports = []
        self.functions = []
        self.classes = []
        self.calls = []
        self.relationships = []
        self._scope = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append({
                "module": alias.name,
                "name": None,
                "alias": alias.asname,
                "line": node.lineno,
            })

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            self.imports.append({
                "module": node.module or "",
                "name": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
            })

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        class_name = node.name
        bases = [_get_name(base) for base in node.bases]
        bases = [base for base in bases if base]

        class_info = {
            "name": class_name,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "bases": bases,
            "methods": [],
        }
        self.classes.append(class_info)

        for base in bases:
            self.relationships.append({
                "type": "inheritance",
                "source": class_name,
                "target": base,
                "line": node.lineno,
            })

        self._scope.append(("class", class_name, class_info))
        for child in node.body:
            self.visit(child)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node) -> None:
        class_scope = next(
            (
                entry
                for entry in reversed(self._scope)
                if entry[0] == "class"
            ),
            None,
        )

        parent_names = [
            entry[1]
            for entry in self._scope
            if entry[0] in {"class", "function"}
        ]
        qualified_name = ".".join(parent_names + [node.name])

        function_info = {
            "name": node.name,
            "qualified_name": qualified_name,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "async": isinstance(node, ast.AsyncFunctionDef),
            "parameters": [
                arg.arg
                for arg in (
                    list(node.args.posonlyargs)
                    + list(node.args.args)
                    + list(node.args.kwonlyargs)
                )
            ],
            "calls": [],
        }

        if class_scope:
            class_scope[2]["methods"].append(function_info)
        else:
            self.functions.append(function_info)

        self._scope.append(("function", node.name, function_info))
        for child in node.body:
            self.visit(child)
        self._scope.pop()

    def visit_Call(self, node: ast.Call) -> None:
        called_name = _get_name(node.func)

        if called_name:
            caller = next(
                (
                    entry[2]["qualified_name"]
                    for entry in reversed(self._scope)
                    if entry[0] == "function"
                ),
                "<module>",
            )

            call_info = {
                "caller": caller,
                "callee": called_name,
                "line": node.lineno,
            }
            self.calls.append(call_info)

            current_function = next(
                (
                    entry[2]
                    for entry in reversed(self._scope)
                    if entry[0] == "function"
                ),
                None,
            )
            if current_function is not None:
                current_function["calls"].append(called_name)

            self.relationships.append({
                "type": "call",
                "source": caller,
                "target": called_name,
                "line": node.lineno,
            })

        self.generic_visit(node)


def analyze_source(
    source: str,
    file_path: str = "<memory>",
) -> dict:
    """Analyze Python source and return JSON-compatible metadata."""
    if not isinstance(source, str):
        raise TypeError("source must be a string.")

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as exc:
        return {
            "file_path": file_path,
            "language": "python",
            "valid": False,
            "syntax_error": {
                "message": exc.msg,
                "line": exc.lineno,
                "column": exc.offset,
            },
            "imports": [],
            "functions": [],
            "classes": [],
            "calls": [],
            "relationships": [],
        }

    analyzer = _SourceAnalyzer()
    analyzer.visit(tree)

    return {
        "file_path": file_path,
        "language": "python",
        "valid": True,
        "syntax_error": None,
        "imports": analyzer.imports,
        "functions": analyzer.functions,
        "classes": analyzer.classes,
        "calls": analyzer.calls,
        "relationships": analyzer.relationships,
    }


def analyze_python_file(file_path: str) -> dict:
    """Read and analyze one Python file."""
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"Python file not found: {file_path}")

    if path.suffix.lower() != ".py":
        raise ValueError("Only .py files are supported by this analyzer.")

    source = path.read_text(encoding="utf-8", errors="replace")
    return analyze_source(source, file_path=path.as_posix())


def analyze_python_repository(
    repository_root: str,
    max_files: int = 1000,
) -> dict:
    """Analyze Python files under a repository directory."""
    root = Path(repository_root).resolve()

    if not root.is_dir():
        raise ValueError(
            f"Repository directory does not exist: {repository_root}"
        )

    if max_files < 1:
        raise ValueError("max_files must be greater than zero.")

    results = []
    errors = []
    truncated = False

    for current, dirnames, filenames in __import__("os").walk(root):
        dirnames[:] = sorted(
            name for name in dirnames if name not in IGNORED_DIRS
        )

        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue

            if len(results) >= max_files:
                truncated = True
                break

            path = Path(current) / filename

            try:
                result = analyze_python_file(str(path))
                result["file_path"] = path.relative_to(root).as_posix()
                results.append(result)
            except (OSError, UnicodeError, ValueError) as exc:
                errors.append({
                    "file_path": path.relative_to(root).as_posix(),
                    "error": str(exc),
                })

        if truncated:
            break

    return {
        "repository": root.name,
        "root_path": str(root),
        "file_count": len(results),
        "valid_file_count": sum(item["valid"] for item in results),
        "invalid_file_count": sum(not item["valid"] for item in results),
        "truncated": truncated,
        "files": results,
        "errors": errors,
    }
