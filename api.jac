
"""Codebase Genius HTTP API."""

import from modules.repository_tools { clone_public_github_repo }
import from agents.supervisor { CodeGeniusSupervisor }
import from agents.doc_genie { DocGenie }


walker:pub health_check {
    can check with Root entry {
        report {
            "status": "ok",
            "service": "Codebase Genius",
            "message": "API is running."
        };
    }
}


walker:pub document_repository {
    has github_url: str;

    can document with Root entry {
        try {
            cloned_path = clone_public_github_repo(
                self.github_url,
                "outputs/repositories"
            );

            supervisor = CodeGeniusSupervisor(
                repository_path=str(cloned_path)
            );

            root spawn supervisor;

            supervisor_result = supervisor.result;

            if supervisor_result["status"] != "success" {
                report {
                    "status": "error",
                    "stage": "supervisor",
                    "details": supervisor_result
                };
            } else {
                documentation = DocGenie(
                    repository_path=str(cloned_path),
                    output_root="outputs"
                );

                root spawn documentation;

                documentation_result = documentation.result;

                if documentation_result["status"] != "success" {
                    report {
                        "status": "error",
                        "stage": "documentation",
                        "details": documentation_result
                    };
                } else {
                    report {
                        "status": "success",
                        "github_url": self.github_url,
                        "repository": documentation_result["repository"],
                        "repository_path": str(cloned_path),
                        "documentation_path": documentation_result["documentation_path"],
                        "diagram_path": documentation_result["diagram_path"],
                        "analysis": {
                            "total_files": supervisor_result["total_files"],
                            "python_files": documentation_result["python_files_analyzed"],
                            "valid_python_files": documentation_result["valid_python_files"],
                            "invalid_python_files": documentation_result["invalid_python_files"],
                            "functions_discovered": documentation_result["functions_discovered"],
                            "classes_discovered": documentation_result["classes_discovered"],
                            "methods_discovered": documentation_result["methods_discovered"],
                            "relationships_discovered": documentation_result["relationships_discovered"],
                            "analysis_truncated": documentation_result["analysis_truncated"]
                        },
                        "priority_files": supervisor_result["priority_files"]
                    };
                }
            }
        } except Exception as exc {
            report {
                "status": "error",
                "stage": "request",
                "message": str(exc)
            };
        }
    }
}
