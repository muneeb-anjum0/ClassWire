"""Reject repository contents that should never reach deployment."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROOTS = {
    ".github",
    ".gitignore",
    "README.md",
    "backend",
    "docs",
    "frontend",
    "tools",
}
FORBIDDEN_NAMES = {
    ".env",
    "client_secret.json",
    "firebase_service_account.json",
    "service-account.json",
    "token.json",
}
FORBIDDEN_SUFFIXES = {".key", ".p12", ".pfx", ".pem"}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    "Google OAuth secret": re.compile(r"GOCSPX-[0-9A-Za-z_-]{20,}"),
    "GitHub token": re.compile(r"(?:ghp_[0-9A-Za-z]{30,}|github_pat_[0-9A-Za-z_]{30,})"),
    "Resend key": re.compile(r"(?<![0-9A-Za-z_])re_[0-9A-Za-z]{20,}(?![0-9A-Za-z_])"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8")


def tracked_files() -> list[Path]:
    return [ROOT / name for name in git("ls-files").splitlines() if name]


def check_repository() -> list[str]:
    errors: list[str] = []
    tracked = tracked_files()

    roots = {path.relative_to(ROOT).parts[0] for path in tracked if path.exists()}
    for name in sorted(roots - ALLOWED_ROOTS):
        errors.append(f"unexpected repository-root entry: {name}")

    modes = {
        line.split(maxsplit=3)[3]: line.split(maxsplit=1)[0]
        for line in git("ls-files", "-s").splitlines()
        if len(line.split(maxsplit=3)) == 4
    }

    for path in tracked:
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        lower_name = path.name.lower()
        mode = modes.get(relative, "")
        if mode == "120000":
            errors.append(f"symbolic links are not allowed: {relative}")
        if mode == "100755":
            errors.append(f"executable tracked file is not allowed: {relative}")
        if lower_name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"secret-bearing file must not be tracked: {relative}")
            continue
        if path.stat().st_size > 1_000_000:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                errors.append(f"possible {label} in {relative}")

    return errors


def main() -> int:
    errors = check_repository()
    if errors:
        print("Repository security guard failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Repository security guard passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
