
import from agents.repo_mapper { RepoMapper }

with entry {
    mapper = RepoMapper(
        repository_path="outputs/repositories/psf_requests"
    );

    root spawn mapper;

    print("\n=== REPO MAPPER SUMMARY ===");
    print(mapper.result);
}
