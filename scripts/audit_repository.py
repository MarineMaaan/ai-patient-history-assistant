"""Review tracked HEAD and staged blobs for obvious secrets/runtime artifacts.

This narrow heuristic supplements manual review; it is not a security audit.
Only repository-tracked/index files are read. Matching payloads are never printed.
"""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
SECRET_PATTERNS = [
    re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(rb"github_pat_[A-Za-z0-9_]{40,}"),
    re.compile(rb"sk-[A-Za-z0-9_-]{30,}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL)


def main() -> int:
    names = git("ls-files", "-z").decode().split("\0")
    findings, inspected = [], 0
    for name in filter(None, names):
        path = Path(name)
        parts = set(path.parts)
        if parts & {"local", ".venv", "__pycache__", ".pytest_cache", "exports", "transcripts", "models"} or path.suffix in {".sqlite3", ".db", ".log", ".gguf", ".safetensors"} or path.name.startswith(".env") or path.name == "secrets.toml":
            findings.append(name + ": prohibited runtime/config artifact")
        for prefix in (":", "HEAD:"):
            try:
                data = git("show", prefix + name)
            except subprocess.CalledProcessError:
                continue  # HEAD may be absent or this path newly added.
            inspected += 1
            if any(pattern.search(data) for pattern in SECRET_PATTERNS):
                findings.append(name + ": possible secret in " + ("index" if prefix == ":" else "HEAD"))
    for finding in findings:
        print(finding)
    print(f"Inspected {inspected} tracked/index blobs; {len(findings)} findings. Manual review still required.")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
