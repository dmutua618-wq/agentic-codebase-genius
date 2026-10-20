
"""Repository mapping, GitHub cloning, and README summarisation."""

import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse


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

IGNORED_FILE_SUFFIXES = {
    ".tmp",
    ".jir",
    ".db-shm",
    ".db-wal",
}

README_NAMES = (
    "README.md",
    "README.rst",
    "README.txt",
    "README",
)


def generate_file_tree(
    root: str,
    max_files: int = 5000,
) -> dict:
    """Generate a structured file tree for a repository."""
    base = Path(root).resolve()

    if not base.is_dir():
        raise ValueError(
            f"Repository directory does not exist: {root}"
        )

    if max_files < 1:
        raise ValueError("max_files must be greater than zero.")

    files = []
    directories = []
    truncated = False

    for current, dirnames, filenames in os.walk(base):
        current_path = Path(current)

        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in IGNORED_DIRS
        )

        relative_dir = current_path.relative_to(base).as_posix()

        if relative_dir != ".":
            directories.append(relative_dir)

        for filename in sorted(filenames):
            file_path = current_path / filename

            if file_path.suffix.lower() in IGNORED_FILE_SUFFIXES:
                continue

            if len(files) >= max_files:
                truncated = True
                break

            try:
                size_bytes = file_path.stat().st_size
            except OSError:
                continue

            files.append({
                "path": file_path.relative_to(base).as_posix(),
                "extension": file_path.suffix.lower(),
                "size_bytes": size_bytes,
            })

        if truncated:
            break

    return {
        "root": base.name,
        "directories": sorted(directories),
        "files": files,
        "file_count": len(files),
        "directory_count": len(directories),
        "truncated": truncated,
    }


def _validate_github_url(url: str) -> tuple[str, str]:
    """Validate a standard public GitHub repository URL."""
    if not isinstance(url, str):
        raise ValueError("The repository URL must be a string.")

    url = url.strip()

    if not url or len(url) > 2048:
        raise ValueError("The repository URL is empty or too long.")

    parsed = urlparse(url)

    if parsed.scheme != "https" or parsed.hostname != "github.com":
        raise ValueError(
            "Use an HTTPS GitHub URL, such as "
            "https://github.com/owner/repository"
        )

    if parsed.username or parsed.password or parsed.port:
        raise ValueError("Credentials and custom ports are not allowed.")

    if parsed.query or parsed.fragment:
        raise ValueError("Repository URLs must not contain query strings.")

    parts = [
        part
        for part in parsed.path.strip("/").split("/")
        if part
    ]

    if len(parts) != 2:
        raise ValueError(
            "Provide a repository URL, not a profile, file, "
            "or subdirectory URL."
        )

    owner, repo = parts

    if repo.endswith(".git"):
        repo = repo[:-4]

    valid_name = re.compile(r"^[A-Za-z0-9_.-]+$")

    if (
        not valid_name.fullmatch(owner)
        or not valid_name.fullmatch(repo)
        or owner in {".", ".."}
        or repo in {".", ".."}
    ):
        raise ValueError(
            "The GitHub owner or repository name is invalid."
        )

    return owner, repo


def _normalise_remote_url(remote_url: str) -> str:
    """Normalize common GitHub remote URL formats for comparison."""
    remote = remote_url.strip()

    if remote.endswith("/"):
        remote = remote[:-1]

    if remote.endswith(".git"):
        remote = remote[:-4]

    if remote.startswith("git@github.com:"):
        remote = "https://github.com/" + remote.split(":", 1)[1]
    elif remote.startswith("ssh://git@github.com/"):
        remote = "https://github.com/" + remote.split(
            "ssh://git@github.com/",
            1,
        )[1]

    return remote.rstrip("/").lower()


def _existing_clone_matches(
    destination: Path,
    expected_remote: str,
) -> bool:
    """Return whether an existing directory is the requested Git clone."""
    if not destination.is_dir():
        return False

    git_metadata = destination / ".git"

    if not git_metadata.exists():
        return False

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(destination),
                "remote",
                "get-url",
                "origin",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

    except FileNotFoundError as exc:
        raise RuntimeError(
            "Git was not found. Install Git for Windows and reopen "
            "your terminal."
        ) from exc

    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "Timed out while checking the existing Git repository."
        ) from exc

    except subprocess.CalledProcessError:
        return False

    actual_remote = _normalise_remote_url(result.stdout)
    expected = _normalise_remote_url(expected_remote)

    return actual_remote == expected


def clone_public_github_repo(
    url: str,
    destination_root: str = "outputs/repositories",
) -> Path:
    """Clone a public GitHub repository or reuse its verified existing clone."""
    owner, repo = _validate_github_url(url)

    destination_base = Path(destination_root).resolve()
    destination_base.mkdir(parents=True, exist_ok=True)

    destination = (
        destination_base / f"{owner}_{repo}"
    ).resolve()

    if destination.parent != destination_base:
        raise ValueError("Invalid repository destination.")

    expected_remote = f"https://github.com/{owner}/{repo}.git"

    if destination.exists():
        if _existing_clone_matches(
            destination,
            expected_remote,
        ):
            return destination

        raise FileExistsError(
            f"Destination already exists but is not a verified clone "
            f"of {expected_remote}: {destination}. "
            "Choose another destination or inspect the directory manually."
        )

    try:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--",
                expected_remote,
                str(destination),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )

    except FileNotFoundError as exc:
        raise RuntimeError(
            "Git was not found. Install Git for Windows and reopen "
            "your terminal."
        ) from exc

    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "Cloning timed out after 180 seconds."
        ) from exc

    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or exc.stdout or "").strip()

        raise RuntimeError(
            "Could not clone the repository. Confirm that it is public, "
            f"the URL is correct, and your internet connection works. "
            f"{message}"
        ) from exc

    return destination


def summarise_readme(repository_root: str) -> dict:
    """Extract a deterministic summary and headings from a README."""
    root = Path(repository_root).resolve()

    if not root.is_dir():
        raise ValueError(
            f"Repository directory does not exist: {repository_root}"
        )

    readme_path = next(
        (
            root / name
            for name in README_NAMES
            if (root / name).is_file()
        ),
        None,
    )

    if readme_path is None:
        return {
            "readme_path": None,
            "title": root.name,
            "summary": "No recognised README file was found.",
            "headings": [],
        }

    content = readme_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    headings = re.findall(
        r"(?m)^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$",
        content,
    )

    title = headings[0] if headings else root.name

    cleaned = re.sub(
        r"```.*?```",
        " ",
        content,
        flags=re.DOTALL,
    )
    cleaned = re.sub(
        r"!\[[^\]]*\]\([^)]*\)",
        " ",
        cleaned,
    )
    cleaned = re.sub(
        r"\[([^\]]+)\]\([^)]*\)",
        r"\1",
        cleaned,
    )
    cleaned = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*[-*+]\s+", "", cleaned)
    cleaned = re.sub(r"[*_`>#]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return {
        "readme_path": readme_path.relative_to(root).as_posix(),
        "title": title,
        "summary": cleaned[:1200],
        "headings": headings[:30],
    }


def map_repository(
    repository_root: str,
    max_files: int = 5000,
) -> dict:
    """Combine file-tree mapping and README summarisation."""
    root = Path(repository_root).resolve()

    tree = generate_file_tree(
        str(root),
        max_files=max_files,
    )

    readme = summarise_readme(str(root))

    extension_counts = {}

    for file_info in tree["files"]:
        extension = file_info["extension"] or "[no extension]"
        extension_counts[extension] = (
            extension_counts.get(extension, 0) + 1
        )

    return {
        "repository": tree["root"],
        "root_path": str(root),
        "file_tree": tree,
        "readme": readme,
        "language_file_counts": extension_counts,
    }
