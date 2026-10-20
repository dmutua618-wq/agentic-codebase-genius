
"""Jac Code Analyzer walker."""

import from modules.code_analysis_service {
    analyze_and_query_repository
}

walker CodeAnalyzer {
    has repository_path: str;
    has max_files: int = 1000;
    has query_symbol: str = "";
    has relationship_type: str = "";
    has result: dict = {};

    can analyze with Root entry {
        try {
            self.result = analyze_and_query_repository(
                self.repository_path,
                self.max_files,
                self.query_symbol,
                self.relationship_type
            );
        } except Exception as exc {
            self.result = {
                "status": "error",
                "message": str(exc)
            };
        }
    }
}
