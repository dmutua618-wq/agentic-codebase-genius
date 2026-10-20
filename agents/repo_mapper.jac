
"""Repo Mapper agent for repository discovery and inventory."""

import from modules.repository_tools { map_repository }

walker RepoMapper {
    has repository_path: str;
    has result: dict = {};

    can map with Root entry {
        try {
            mapped = map_repository(self.repository_path);

            self.result = {
                "status": "success",
                "repository": mapped["repository"],
                "root_path": mapped["root_path"],
                "file_tree": mapped["file_tree"],
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
