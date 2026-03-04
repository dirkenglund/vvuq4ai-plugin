"""
Code Hygiene Tests for VVUQ4AI Claude Code Plugin

Critic-generated tests that scan the actual plugin directory tree and file
contents to enforce distribution-quality hygiene standards.

Run:
    pytest tests/critic-generated/test_hygiene_violations.py -v
"""
import json
import os
import stat
from pathlib import Path

import pytest

# Plugin root: tests/critic-generated/../../ -> plugin root
PLUGIN_ROOT = Path(__file__).parent.parent.parent.resolve()

# Directories to skip when scanning.
# .git: git internals are never distributed
# __pycache__, .pytest_cache, .benchmarks: created at runtime by pytest, not pre-existing
SKIP_DIRS = {".git", ".github", "__pycache__", ".pytest_cache", ".benchmarks"}

# ─── Helpers ────────────────────────────────────────────────────────────────


def _walk_files(root: Path):
    """Yield all files under root, excluding .git/."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            yield Path(dirpath) / fname


def _walk_dirs(root: Path):
    """Yield all directories under root (not root itself), excluding .git/."""
    for dirpath, dirnames, _filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for dname in dirnames:
            yield Path(dirpath) / dname


def _text_files(root: Path):
    """Yield text files (non-binary) under root, excluding .git/."""
    for fpath in _walk_files(root):
        try:
            fpath.read_text(encoding="utf-8")
            yield fpath
        except (UnicodeDecodeError, ValueError):
            continue


# ─── 1. Empty Directories ──────────────────────────────────────────────────


class TestEmptyDirectories:
    """Empty directories should not exist in a distributed plugin.

    Git does not track empty directories, so they indicate either
    scaffolding leftovers or missing content. The hooks/ and hooks/scripts/
    directories are known offenders.
    """

    def test_no_empty_directories(self):
        """Every directory must contain at least one file (recursively)."""
        empty_dirs = []
        for d in _walk_dirs(PLUGIN_ROOT):
            # A directory is "empty" if it contains zero files at any depth
            has_files = any(
                f.is_file()
                for f in d.rglob("*")
                if not any(p.name in SKIP_DIRS for p in f.parents)
            )
            if not has_files:
                empty_dirs.append(str(d.relative_to(PLUGIN_ROOT)))

        assert empty_dirs == [], (
            f"Empty directories found (should be removed or populated): "
            f"{empty_dirs}"
        )

    def test_hooks_directory_has_content(self):
        """The hooks/ directory must contain actual hook files, not just empty subdirs."""
        hooks_dir = PLUGIN_ROOT / "hooks"
        if not hooks_dir.exists():
            pytest.skip("hooks/ directory does not exist")

        hook_files = [
            f
            for f in hooks_dir.rglob("*")
            if f.is_file()
        ]
        assert len(hook_files) > 0, (
            "hooks/ directory exists but contains no files. "
            "Either populate it with hook scripts or remove it entirely."
        )

    def test_hooks_scripts_directory_has_content(self):
        """The hooks/scripts/ directory must contain script files."""
        scripts_dir = PLUGIN_ROOT / "hooks" / "scripts"
        if not scripts_dir.exists():
            pytest.skip("hooks/scripts/ directory does not exist")

        script_files = list(scripts_dir.iterdir())
        assert len(script_files) > 0, (
            "hooks/scripts/ directory exists but is empty. "
            "Either add scripts or remove the directory."
        )


# ─── 2. Gitignore Coverage ─────────────────────────────────────────────────


class TestGitignoreCoverage:
    """The .gitignore must cover common OS, editor, and language artifacts."""

    REQUIRED_PATTERNS = {
        ".DS_Store": "macOS Finder metadata",
        "__pycache__/": "Python bytecode cache",
        "*.pyc": "Python compiled files",
        "node_modules/": "Node.js dependencies",
        ".env": "Environment variable secrets",
    }

    RECOMMENDED_PATTERNS = {
        "*.log": "Log files from development/testing",
        "*.bak": "Backup files from editors",
        ".vscode/": "VS Code editor config",
        ".idea/": "JetBrains IDE config",
        "*.swp": "Vim swap files",
        "*.swo": "Vim swap files",
        "*~": "Emacs/editor backup files",
        "dist/": "Build output directory",
        "build/": "Build output directory",
        "*.egg-info/": "Python egg metadata",
    }

    @pytest.fixture()
    def gitignore_content(self):
        gitignore_path = PLUGIN_ROOT / ".gitignore"
        assert gitignore_path.exists(), ".gitignore file is missing entirely"
        return gitignore_path.read_text(encoding="utf-8")

    @pytest.fixture()
    def gitignore_lines(self, gitignore_content):
        """Return non-comment, non-blank lines from .gitignore."""
        return [
            line.strip()
            for line in gitignore_content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

    def test_gitignore_exists(self):
        assert (PLUGIN_ROOT / ".gitignore").exists(), (
            ".gitignore is missing from plugin root"
        )

    @pytest.mark.parametrize(
        "pattern,reason",
        list(REQUIRED_PATTERNS.items()),
        ids=list(REQUIRED_PATTERNS.keys()),
    )
    def test_required_gitignore_pattern(self, gitignore_lines, pattern, reason):
        """Each required pattern must be present in .gitignore."""
        assert pattern in gitignore_lines, (
            f".gitignore is missing required pattern '{pattern}' ({reason}). "
            f"Current patterns: {gitignore_lines}"
        )

    @pytest.mark.parametrize(
        "pattern,reason",
        list(RECOMMENDED_PATTERNS.items()),
        ids=list(RECOMMENDED_PATTERNS.keys()),
    )
    def test_recommended_gitignore_pattern(self, gitignore_lines, pattern, reason):
        """Recommended patterns should be in .gitignore for a distributed plugin."""
        assert pattern in gitignore_lines, (
            f".gitignore is missing recommended pattern '{pattern}' ({reason}). "
            f"Consider adding it for a publicly distributed plugin."
        )


# ─── 3. Trailing Whitespace ────────────────────────────────────────────────


class TestTrailingWhitespace:
    """No text file should have trailing whitespace on any line."""

    def test_no_trailing_whitespace(self):
        violations = []
        for fpath in _text_files(PLUGIN_ROOT):
            content = fpath.read_text(encoding="utf-8")
            for lineno, line in enumerate(content.splitlines(), start=1):
                if line != line.rstrip():
                    rel = fpath.relative_to(PLUGIN_ROOT)
                    violations.append(f"{rel}:{lineno}")
                    break  # One violation per file is enough

        assert violations == [], (
            f"Files with trailing whitespace: {violations}"
        )


# ─── 4. Consistent Line Endings ────────────────────────────────────────────


class TestLineEndings:
    """All text files must use LF line endings. No CRLF or mixed."""

    def test_no_crlf_line_endings(self):
        violations = []
        for fpath in _text_files(PLUGIN_ROOT):
            raw = fpath.read_bytes()
            if b"\r\n" in raw:
                rel = fpath.relative_to(PLUGIN_ROOT)
                violations.append(str(rel))

        assert violations == [], (
            f"Files with CRLF line endings (should be LF only): {violations}"
        )

    def test_no_lone_cr_line_endings(self):
        """Old Mac-style CR-only line endings should not exist."""
        violations = []
        for fpath in _text_files(PLUGIN_ROOT):
            raw = fpath.read_bytes()
            # Check for \r not followed by \n
            stripped = raw.replace(b"\r\n", b"")
            if b"\r" in stripped:
                rel = fpath.relative_to(PLUGIN_ROOT)
                violations.append(str(rel))

        assert violations == [], (
            f"Files with CR-only line endings: {violations}"
        )


# ─── 5. File Bloat ─────────────────────────────────────────────────────────


class TestFileBloat:
    """No unnecessary binary files, OS metadata, or bloat in distribution."""

    UNWANTED_FILENAMES = {
        ".DS_Store",
        "Thumbs.db",
        "desktop.ini",
        ".directory",
    }

    UNWANTED_EXTENSIONS = {
        ".pyc",
        ".pyo",
        ".class",
        ".o",
        ".so",
        ".dll",
        ".dylib",
        ".exe",
        ".bin",
    }

    def test_no_os_metadata_files(self):
        violations = []
        for fpath in _walk_files(PLUGIN_ROOT):
            if fpath.name in self.UNWANTED_FILENAMES:
                violations.append(str(fpath.relative_to(PLUGIN_ROOT)))

        assert violations == [], (
            f"OS metadata files found (add to .gitignore and remove): {violations}"
        )

    def test_no_compiled_binary_artifacts(self):
        violations = []
        for fpath in _walk_files(PLUGIN_ROOT):
            if fpath.suffix.lower() in self.UNWANTED_EXTENSIONS:
                violations.append(str(fpath.relative_to(PLUGIN_ROOT)))

        assert violations == [], (
            f"Compiled/binary artifacts found: {violations}"
        )

    def test_no_node_modules(self):
        nm = PLUGIN_ROOT / "node_modules"
        assert not nm.exists(), (
            "node_modules/ directory exists and should not be distributed"
        )

    def test_no_pycache(self):
        violations = []
        for d in _walk_dirs(PLUGIN_ROOT):
            if d.name == "__pycache__":
                violations.append(str(d.relative_to(PLUGIN_ROOT)))

        assert violations == [], (
            f"__pycache__ directories found: {violations}"
        )


# ─── 6. Debug / Dev Artifacts ──────────────────────────────────────────────


class TestDevArtifacts:
    """No IDE configs, log files, backup files, or debug artifacts."""

    DEV_DIRS = {".vscode", ".idea", ".vs", ".fleet", "__pycache__"}

    DEV_EXTENSIONS = {".log", ".bak", ".tmp", ".swp", ".swo"}

    DEV_FILES = {".env", ".env.local", ".env.development", ".env.production"}

    def test_no_ide_directories(self):
        violations = []
        for d in _walk_dirs(PLUGIN_ROOT):
            if d.name in self.DEV_DIRS:
                violations.append(str(d.relative_to(PLUGIN_ROOT)))

        assert violations == [], (
            f"IDE/dev directories found (should not be distributed): {violations}"
        )

    def test_no_log_or_backup_files(self):
        violations = []
        for fpath in _walk_files(PLUGIN_ROOT):
            if fpath.suffix.lower() in self.DEV_EXTENSIONS:
                violations.append(str(fpath.relative_to(PLUGIN_ROOT)))

        assert violations == [], (
            f"Log/backup/temp files found: {violations}"
        )

    def test_no_env_files(self):
        violations = []
        for fpath in _walk_files(PLUGIN_ROOT):
            if fpath.name in self.DEV_FILES:
                violations.append(str(fpath.relative_to(PLUGIN_ROOT)))

        assert violations == [], (
            f".env files found (may contain secrets!): {violations}"
        )


# ─── 7. File Permissions ───────────────────────────────────────────────────


class TestFilePermissions:
    """Non-script text files should not have executable bits set."""

    # Files that ARE allowed to be executable
    ALLOWED_EXECUTABLE_EXTENSIONS = {".sh", ".bash", ".zsh", ".fish", ".py"}
    ALLOWED_EXECUTABLE_DIRS = {"scripts", "bin", "hooks"}

    def test_no_executable_text_files(self):
        """Text files outside of script directories should not be executable."""
        violations = []
        for fpath in _text_files(PLUGIN_ROOT):
            st = fpath.stat()
            is_exec = st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            if is_exec:
                # Allow if extension or parent dir suggests it should be executable
                in_script_dir = any(
                    p.name in self.ALLOWED_EXECUTABLE_DIRS
                    for p in fpath.parents
                )
                has_script_ext = fpath.suffix in self.ALLOWED_EXECUTABLE_EXTENSIONS
                if not (in_script_dir or has_script_ext):
                    violations.append(str(fpath.relative_to(PLUGIN_ROOT)))

        assert violations == [], (
            f"Non-script files with executable permissions: {violations}"
        )


# ─── 8. JSON Validity ──────────────────────────────────────────────────────


class TestJsonValidity:
    """All .json files must be valid JSON."""

    def test_all_json_files_parse(self):
        violations = []
        for fpath in _walk_files(PLUGIN_ROOT):
            if fpath.suffix == ".json":
                try:
                    content = fpath.read_text(encoding="utf-8")
                    json.loads(content)
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    rel = fpath.relative_to(PLUGIN_ROOT)
                    violations.append(f"{rel}: {exc}")

        assert violations == [], (
            f"Invalid JSON files: {violations}"
        )


# ─── 9. Files End with Newline ──────────────────────────────────────────────


class TestFinalNewline:
    """POSIX convention: text files should end with a newline character."""

    def test_all_text_files_end_with_newline(self):
        violations = []
        for fpath in _text_files(PLUGIN_ROOT):
            content = fpath.read_bytes()
            if len(content) > 0 and not content.endswith(b"\n"):
                violations.append(str(fpath.relative_to(PLUGIN_ROOT)))

        assert violations == [], (
            f"Files not ending with a newline: {violations}"
        )


# ─── 10. No Secrets or Credentials ─────────────────────────────────────────


class TestNoSecrets:
    """Plugin should not contain hardcoded secrets, API keys, or tokens."""

    SECRET_PATTERNS = [
        "PRIVATE KEY",
        "sk-",        # OpenAI-style API key prefix
        "ghp_",       # GitHub personal access token prefix
        "gho_",       # GitHub OAuth token prefix
        "Bearer ",    # Auth header with literal token
        "password=",
        "api_key=",
        "secret_key=",
    ]

    # Files allowed to reference these patterns:
    # - Documentation files that discuss patterns as examples
    ALLOWED_FILES = {"README.md", "SKILL.md", "verify.md", "vvuq-verifier.md"}

    # Directories whose files may legitimately contain pattern strings
    # (e.g. test files define patterns as scan targets)
    ALLOWED_DIRS = {"tests"}

    def test_no_hardcoded_secrets(self):
        violations = []
        for fpath in _text_files(PLUGIN_ROOT):
            if fpath.name in self.ALLOWED_FILES:
                continue
            # Skip files inside allowed directories (tests contain patterns as literals)
            try:
                rel = fpath.relative_to(PLUGIN_ROOT)
                if any(part in self.ALLOWED_DIRS for part in rel.parts):
                    continue
            except ValueError:
                pass
            content = fpath.read_text(encoding="utf-8")
            for pattern in self.SECRET_PATTERNS:
                if pattern in content:
                    rel = fpath.relative_to(PLUGIN_ROOT)
                    violations.append(f"{rel} contains '{pattern}'")

        assert violations == [], (
            f"Possible hardcoded secrets found: {violations}"
        )


# ─── 11. Required Plugin Files ─────────────────────────────────────────────


class TestRequiredFiles:
    """A marketplace plugin must have certain files present."""

    REQUIRED = [
        ".claude-plugin/plugin.json",
        ".mcp.json",
        "README.md",
        "LICENSE",
        ".gitignore",
    ]

    @pytest.mark.parametrize("rel_path", REQUIRED)
    def test_required_file_exists(self, rel_path):
        fpath = PLUGIN_ROOT / rel_path
        assert fpath.exists(), (
            f"Required plugin file missing: {rel_path}"
        )

    def test_plugin_json_has_required_fields(self):
        pjson = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
        data = json.loads(pjson.read_text(encoding="utf-8"))

        required_fields = {"name", "version", "description"}
        missing = required_fields - set(data.keys())
        assert missing == set(), (
            f"plugin.json missing required fields: {missing}"
        )

    def test_at_least_one_command_or_agent_or_skill(self):
        """Plugin must provide at least one of: command, agent, or skill."""
        has_command = any((PLUGIN_ROOT / "commands").rglob("*.md"))
        has_agent = any((PLUGIN_ROOT / "agents").rglob("*.md"))
        has_skill = any((PLUGIN_ROOT / "skills").rglob("*.md"))

        assert has_command or has_agent or has_skill, (
            "Plugin must provide at least one command, agent, or skill"
        )


# ─── 12. GitHub Actions Workflow Hygiene (Round 3) ───────────────────────────
#
# .github is in SKIP_DIRS so the general hygiene scanners never touch
# .github/workflows/tests.yml.  These tests fill that gap with targeted
# checks on the workflow file itself.


class TestGitHubWorkflowHygiene:
    """Targeted hygiene checks for .github/workflows/tests.yml.

    Because SKIP_DIRS excludes .github from all general scanners, none of the
    earlier tests (trailing whitespace, CRLF, final newline, YAML validity,
    secrets) exercise the workflow file.  These tests close that gap and add
    CI-specific quality gates.
    """

    WORKFLOW_PATH = PLUGIN_ROOT / ".github" / "workflows" / "tests.yml"

    @pytest.fixture(autouse=True)
    def require_workflow(self):
        if not self.WORKFLOW_PATH.exists():
            pytest.skip(".github/workflows/tests.yml does not exist")

    # ── 12a. Basic text hygiene (mirrors skipped general tests) ──────────────

    def test_workflow_no_trailing_whitespace(self):
        """tests.yml must have no trailing whitespace on any line.

        The general TestTrailingWhitespace scanner skips .github/ via SKIP_DIRS
        so this check would otherwise go undetected.
        """
        content = self.WORKFLOW_PATH.read_text(encoding="utf-8")
        violations = []
        for lineno, line in enumerate(content.splitlines(), start=1):
            if line != line.rstrip(" \t"):
                violations.append(f"line {lineno}: {line!r}")
        assert violations == [], (
            f".github/workflows/tests.yml has trailing whitespace: {violations}"
        )

    def test_workflow_no_crlf_line_endings(self):
        """tests.yml must use LF line endings only.

        The general TestLineEndings scanner skips .github/ via SKIP_DIRS.
        """
        raw = self.WORKFLOW_PATH.read_bytes()
        assert b"\r\n" not in raw, (
            ".github/workflows/tests.yml contains CRLF line endings (must be LF only)"
        )

    def test_workflow_ends_with_newline(self):
        """tests.yml must end with a newline character (POSIX convention).

        The general TestFinalNewline scanner skips .github/ via SKIP_DIRS.
        """
        raw = self.WORKFLOW_PATH.read_bytes()
        assert len(raw) > 0 and raw.endswith(b"\n"), (
            ".github/workflows/tests.yml does not end with a newline"
        )

    def test_workflow_yaml_is_valid(self):
        """tests.yml must parse as valid YAML without errors."""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed; cannot validate workflow YAML")

        content = self.WORKFLOW_PATH.read_text(encoding="utf-8")
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as exc:
            pytest.fail(
                f".github/workflows/tests.yml is not valid YAML: {exc}"
            )

    def test_workflow_no_secrets_hardcoded(self):
        """tests.yml must not contain hardcoded tokens or API keys.

        The general TestNoSecrets scanner skips .github/ via SKIP_DIRS.
        """
        secret_patterns = ["ghp_", "gho_", "sk-", "PRIVATE KEY", "api_key="]
        content = self.WORKFLOW_PATH.read_text(encoding="utf-8")
        for pattern in secret_patterns:
            assert pattern not in content, (
                f".github/workflows/tests.yml contains suspect secret pattern: '{pattern}'"
            )

    # ── 12b. CI correctness and safety ───────────────────────────────────────

    def test_workflow_has_timeout_minutes(self):
        """The CI job must declare timeout-minutes to prevent runaway builds.

        Without a timeout, a hung process (e.g. a test waiting on a
        network resource) will consume CI minutes until the platform's
        default 6-hour limit is reached.  A value of 15 minutes is
        sufficient for the current test suite.
        """
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")

        data = yaml.safe_load(self.WORKFLOW_PATH.read_text(encoding="utf-8"))
        # PyYAML 1.1: bare 'on' key becomes boolean True
        trigger_key = True if True in data else "on"
        jobs = data.get("jobs", {})
        assert jobs, ".github/workflows/tests.yml has no jobs defined"

        for job_name, job_cfg in jobs.items():
            assert "timeout-minutes" in job_cfg, (
                f"Job '{job_name}' in tests.yml is missing 'timeout-minutes'. "
                "Add e.g. 'timeout-minutes: 15' to prevent runaway CI builds."
            )

    def test_workflow_uses_pinned_action_shas_or_major_tags(self):
        """Action references must use a version tag or SHA, never a bare branch name.

        Using 'actions/checkout@main' would silently pick up upstream changes
        and is a supply-chain risk.  Tags like '@v4' or full SHAs are required.
        """
        import re

        content = self.WORKFLOW_PATH.read_text(encoding="utf-8")
        # Find 'uses: owner/repo@ref' lines
        unpinned = []
        for lineno, line in enumerate(content.splitlines(), start=1):
            m = re.search(r"uses:\s+\S+@(\S+)", line)
            if m:
                ref = m.group(1)
                # Reject bare branch names: main, master, latest, HEAD, develop
                if re.fullmatch(r"(main|master|latest|HEAD|develop)", ref, re.IGNORECASE):
                    unpinned.append(f"line {lineno}: {line.strip()}")
        assert unpinned == [], (
            f"Workflow uses unpinned (branch-ref) action versions: {unpinned}. "
            "Use a version tag (e.g. @v4) or a full commit SHA."
        )


# ─── 13. .gitignore *.html Pattern (Round 3) ─────────────────────────────────
#
# *.html was added to .gitignore in this round to suppress generated HTML
# coverage/benchmark reports.  The existing parametrised tests only check
# REQUIRED_PATTERNS and RECOMMENDED_PATTERNS, neither of which includes *.html.
# This test pins the new pattern so it cannot be accidentally removed.


class TestGitignoreHtmlPattern:
    """The *.html pattern added in round 3 must remain in .gitignore."""

    def test_html_pattern_in_gitignore(self):
        """*.html must be present in .gitignore to suppress generated reports.

        Added in round 3 to prevent HTML coverage/benchmark output from being
        accidentally committed.  This test pins the pattern so it cannot be
        silently removed in future edits.
        """
        gitignore_path = PLUGIN_ROOT / ".gitignore"
        assert gitignore_path.exists(), ".gitignore is missing"

        lines = [
            line.strip()
            for line in gitignore_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert "*.html" in lines, (
            "*.html pattern is missing from .gitignore. "
            "It was added in round 3 to suppress generated HTML reports; "
            "do not remove it."
        )
