import from agents.code_analyzer { CodeAnalyzer }

with entry {
    analyzer = CodeAnalyzer(
        repository_path="outputs/repositories/psf_requests",
        query_symbol="request",
        relationship_type="call"
    );

    root spawn analyzer;

    print("\n=== CODE ANALYZER RESULT ===");
    print(analyzer.result);
}
