
import from agents.supervisor { CodeGeniusSupervisor }
import from agents.doc_genie { DocGenie }

with entry {
    print("==========================================");
    print("          CODEBASE GENIUS");
    print("       Agentic Code Documentation");
    print("==========================================");

    supervisor = CodeGeniusSupervisor(
        repository_path="."
    );

    root spawn supervisor;

    print("");
    print("Supervisor results:");
    print(supervisor.result);

    print("");
    print("DocGenie results:");

    documentation = DocGenie(
        repository_path=".",
        output_root="outputs"
    );

    root spawn documentation;

    print(documentation.result);
}
