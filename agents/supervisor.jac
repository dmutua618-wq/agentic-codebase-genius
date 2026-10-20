import from modules.repository_tools { map_repository }
import from modules.source_parser { analyze_python_repository }

node RepositorySnapshot {
    has repository_name: str;
    has root_path: str;
    has file_count: int;
    has python_file_count: int;
    has valid_python_files: int;
    has invalid_python_files: int;
    has prioritized_files: list[str];
}

edge HasSnapshot {}

walker CodeGeniusSupervisor {
    has repository_path: str;
    has result: dict = {};

    can orchestrate with Root entry {
        try {
            mapped = map_repository(self.repository_path);
            analysis = analyze_python_repository(self.repository_path);

            repository_name: str = str(mapped["repository"]);
            root_path: str = str(mapped["root_path"]);
            total_files: int = int(mapped["file_tree"]["file_count"]);

            python_files: int = int(analysis["file_count"]);
            valid_files: int = int(analysis["valid_file_count"]);
            invalid_files: int = int(analysis["invalid_file_count"]);

            prioritized_files: list[str] = [];
            entry_names: list[str] = [
                "main.py",
                "app.py",
                "api.py",
                "__main__.py",
                "cli.py",
                "server.py"
            ];

            # Stage 1: prioritize common application entry points.
            for file_info in mapped["file_tree"]["files"] {
                path: str = str(file_info["path"]);
                filename: str = path.split("/")[-1];
                parts: list[str] = path.split("/");
                extension: str = str(file_info["extension"]);

                is_test: bool = (
                    "tests" in parts
                    or "test" in parts
                    or filename.startswith("test_")
                    or filename.endswith("_test.py")
                );

                if (
                    extension == ".py"
                    and not is_test
                    and (
                        filename in entry_names
                        or filename.startswith("main.")
                        or filename.startswith("app.")
                    )
                ) {
                    if path not in prioritized_files {
                        prioritized_files.append(path);
                    }
                }
            }

            # Stage 2: prioritize production modules under src/.
            for file_info in mapped["file_tree"]["files"] {
                path: str = str(file_info["path"]);
                filename: str = path.split("/")[-1];
                parts: list[str] = path.split("/");
                extension: str = str(file_info["extension"]);

                is_test: bool = (
                    "tests" in parts
                    or "test" in parts
                    or filename.startswith("test_")
                    or filename.endswith("_test.py")
                );

                if (
                    extension == ".py"
                    and path.startswith("src/")
                    and not is_test
                    and path not in prioritized_files
                    and len(prioritized_files) < 5
                ) {
                    prioritized_files.append(path);
                }
            }

            

            snapshot = RepositorySnapshot(
                repository_name=repository_name,
                root_path=root_path,
                file_count=total_files,
                python_file_count=python_files,
                valid_python_files=valid_files,
                invalid_python_files=invalid_files,
                prioritized_files=prioritized_files
            );

            here ++> snapshot;

            self.result = {
                "status": "success",
                "repository": repository_name,
                "root_path": root_path,
                "total_files": total_files,
                "python_files": python_files,
                "valid_python_files": valid_files,
                "invalid_python_files": invalid_files,
                "file_tree_truncated": bool(mapped["file_tree"]["truncated"]),
                "analysis_truncated": bool(analysis["truncated"]),
                "priority_files": prioritized_files,
                "readme": mapped["readme"],
                "language_file_counts": mapped["language_file_counts"]
            };

        } except Exception as exc {
            self.result = {
                "status": "error",
                "message": str(exc)
            };
        }
    }
}

