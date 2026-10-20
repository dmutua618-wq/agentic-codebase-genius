
import from modules.doc_generator { generate_documentation }

walker DocGenie {
    has repository_path: str;
    has output_root: str = "outputs";
    has result: dict = {};

    can generate with Root entry {
        try {
            self.result = generate_documentation(
                self.repository_path,
                self.output_root
            );
        } except Exception as exc {
            self.result = {
                "status": "error",
                "message": str(exc)
            };
        }
    }
}
