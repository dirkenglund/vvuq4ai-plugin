"""
Performance critic tests for the VVUQ4AI Claude Code plugin.

These tests check for distribution bloat, redundant configuration,
token waste, model selection, and false-trigger risk in skill descriptions.

Run:
    pytest tests/critic-generated/test_performance_violations.py -v
"""

import json
import pathlib
import re

import pytest

PLUGIN_ROOT = pathlib.Path(__file__).parent.parent.parent

# Directories that are NOT part of the distributed plugin
_EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", ".benchmarks", "tests"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _distribution_files():
    """Return files that would be distributed to users (excludes .git,
    __pycache__, tests, .pytest_cache, .benchmarks)."""
    return [
        p
        for p in PLUGIN_ROOT.rglob("*")
        if p.is_file() and not any(ex in p.parts for ex in _EXCLUDED_DIRS)
    ]


def _all_content_files():
    """Return all non-.git, non-cache files in the plugin tree (includes tests)."""
    _cache_dirs = {".git", "__pycache__", ".pytest_cache", ".benchmarks"}
    return [
        p
        for p in PLUGIN_ROOT.rglob("*")
        if p.is_file() and not any(ex in p.parts for ex in _cache_dirs)
    ]


def _read_text(rel: str) -> str:
    return (PLUGIN_ROOT / rel).read_text(encoding="utf-8")


def _approx_tokens(text: str) -> int:
    """Rough token estimate: ~0.75 tokens per word (conservative for English + code)."""
    words = len(text.split())
    return int(words * 1.33)  # inverse: 1 word ~ 1.33 tokens


# ===========================================================================
# 1. Total plugin size — should be small for marketplace distribution
# ===========================================================================

class TestPluginSize:

    def test_total_distribution_size_under_20kb(self):
        """Distributed plugin files (excluding tests, caches) should be under
        20 KB for fast install. Config + markdown only."""
        files = _distribution_files()
        total = sum(p.stat().st_size for p in files)
        assert total < 20_000, (
            f"Distribution is {total:,} bytes — exceeds 20 KB. "
            f"Files: {[(str(p.relative_to(PLUGIN_ROOT)), p.stat().st_size) for p in files]}"
        )

    def test_no_distribution_file_exceeds_5kb(self):
        """No single config/instruction file should exceed 5 KB."""
        for p in _distribution_files():
            size = p.stat().st_size
            assert size < 5_000, (
                f"{p.relative_to(PLUGIN_ROOT)} is {size:,} bytes — "
                "consider trimming to reduce token load."
            )

    def test_distribution_file_count_reasonable(self):
        """Distributed plugin should have fewer than 15 files (lean distribution)."""
        files = _distribution_files()
        count = len(files)
        assert count < 15, (
            f"Plugin distributes {count} files. A lean plugin should have <15."
        )


# ===========================================================================
# 2. Redundant configuration — plugin.json vs marketplace.json overlap
# ===========================================================================

class TestConfigRedundancy:

    @pytest.mark.xfail(reason="marketplace.json requires these fields per Claude Code spec")
    def test_duplicated_fields_between_plugin_and_marketplace(self):
        """plugin.json and marketplace.json should not repeat the same data
        unnecessarily. If both are required by the spec, this is informational;
        if not, one should be the source of truth."""
        plugin = json.loads(_read_text(".claude-plugin/plugin.json"))
        marketplace = json.loads(_read_text(".claude-plugin/marketplace.json"))

        # Extract the first plugin entry from marketplace
        mp_entry = marketplace.get("plugins", [{}])[0]

        duplicated = []
        for key in ("name", "version", "description", "license"):
            pval = plugin.get(key)
            mval = mp_entry.get(key) or marketplace.get("metadata", {}).get(key)
            if pval and mval and pval == mval:
                duplicated.append(key)

        # Having 1–2 shared fields (name, version) is expected as identifiers.
        # Having 3+ identical fields signals copy-paste bloat.
        assert len(duplicated) <= 2, (
            f"Fields duplicated across plugin.json and marketplace.json: {duplicated}. "
            "Consider removing redundant fields from marketplace.json or referencing "
            "plugin.json values."
        )

    def test_marketplace_repository_consistency(self):
        """The repository URL should be consistent between the two config files."""
        plugin = json.loads(_read_text(".claude-plugin/plugin.json"))
        marketplace = json.loads(_read_text(".claude-plugin/marketplace.json"))
        mp_entry = marketplace.get("plugins", [{}])[0]

        p_repo = plugin.get("repository", "")
        m_repo = mp_entry.get("repository", "")

        if p_repo and m_repo:
            assert p_repo == m_repo, (
                f"Repository mismatch: plugin.json says '{p_repo}', "
                f"marketplace.json says '{m_repo}'. Users will be confused."
            )


# ===========================================================================
# 3. Empty directories — dead weight in distribution
# ===========================================================================

class TestEmptyDirectories:

    def test_no_empty_leaf_directories_in_distribution(self):
        """Directories with no distributable files are dead weight and confuse users.
        Excludes .git, __pycache__, .pytest_cache, .benchmarks, and tests/."""
        empty_dirs = []
        for d in PLUGIN_ROOT.rglob("*"):
            if not d.is_dir():
                continue
            if any(ex in d.parts for ex in _EXCLUDED_DIRS):
                continue
            # Check if this directory (recursively) has any distributable files
            has_dist_files = any(
                f.is_file()
                for f in d.rglob("*")
                if not any(ex in f.parts for ex in _EXCLUDED_DIRS)
            )
            if not has_dist_files:
                empty_dirs.append(str(d.relative_to(PLUGIN_ROOT)))

        assert not empty_dirs, (
            f"Empty directories found in distribution tree: {empty_dirs}. "
            "Remove or populate them before marketplace submission."
        )


# ===========================================================================
# 4. MCP endpoint config efficiency
# ===========================================================================

class TestMcpConfig:

    def test_mcp_url_uses_https(self):
        """MCP endpoint must use HTTPS for security."""
        mcp = json.loads(_read_text(".mcp.json"))
        for name, cfg in mcp.get("mcpServers", {}).items():
            url = cfg.get("url", "")
            assert url.startswith("https://"), (
                f"MCP server '{name}' uses non-HTTPS URL: {url}"
            )

    def test_mcp_url_has_no_redundant_params(self):
        """URL should be clean — no query params, fragments, or double slashes
        (except the protocol)."""
        mcp = json.loads(_read_text(".mcp.json"))
        for name, cfg in mcp.get("mcpServers", {}).items():
            url = cfg.get("url", "")
            assert "?" not in url, (
                f"MCP URL for '{name}' has query params — should be clean base URL."
            )
            assert "#" not in url, (
                f"MCP URL for '{name}' has fragment — not appropriate for SSE endpoint."
            )
            # Check for double slashes beyond protocol
            path_part = url.split("://", 1)[-1]
            assert "//" not in path_part, (
                f"MCP URL for '{name}' has double slashes in path: {url}"
            )

    def test_mcp_json_has_single_server(self):
        """For a single-purpose plugin, only 1 MCP server should be declared."""
        mcp = json.loads(_read_text(".mcp.json"))
        count = len(mcp.get("mcpServers", {}))
        assert count == 1, (
            f".mcp.json declares {count} servers — a single-purpose plugin "
            "should have exactly 1."
        )

    def test_mcp_config_is_minimal(self):
        """MCP config should only contain the required keys, no extras."""
        mcp = json.loads(_read_text(".mcp.json"))
        for name, cfg in mcp.get("mcpServers", {}).items():
            allowed_keys = {"url", "command", "args", "env", "transport"}
            extra = set(cfg.keys()) - allowed_keys
            assert not extra, (
                f"MCP server '{name}' has unexpected config keys: {extra}. "
                "Remove to keep config lean."
            )


# ===========================================================================
# 5. Agent model selection
# ===========================================================================

class TestAgentModelSelection:

    @pytest.mark.xfail(reason="Product decision: sonnet chosen for verification quality over cost")
    def test_agent_uses_cost_appropriate_model(self):
        """The vvuq-verifier agent dispatches to an MCP tool and formats
        results. This is a structured, low-reasoning task. Using 'sonnet'
        instead of 'haiku' costs ~5x more per invocation. For a publicly
        distributed plugin where users pay for their own tokens, 'sonnet'
        may be unnecessarily expensive.

        This test FAILS to flag the issue for human review — the right model
        is a product decision, not a strict bug."""
        agent_text = _read_text("agents/vvuq-verifier.md")
        # Extract YAML frontmatter model field
        match = re.search(r"^model:\s*(\S+)", agent_text, re.MULTILINE)
        assert match, "Agent file has no 'model' field in frontmatter."
        model = match.group(1).lower()

        # Flag if using a model more expensive than haiku for what is
        # essentially tool dispatch + formatting
        expensive_models = {"sonnet", "opus", "claude-3-opus", "claude-3-sonnet",
                            "claude-3.5-sonnet", "claude-sonnet-4", "claude-opus-4"}
        if model in expensive_models:
            # This is a soft advisory — change to a warning if you want it non-blocking
            assert False, (
                f"Agent model is '{model}'. For an MCP dispatch + formatting task, "
                "'haiku' would reduce cost ~5x while maintaining quality. "
                "Consider making this configurable or defaulting to 'haiku'."
            )


# ===========================================================================
# 6. Token consumption — instruction verbosity
# ===========================================================================

class TestTokenConsumption:

    def test_agent_instructions_under_700_tokens(self):
        """Agent system prompt should be concise. Every token is consumed
        on every agent invocation. Allow 700 for error handling docs."""
        text = _read_text("agents/vvuq-verifier.md")
        tokens = _approx_tokens(text)
        assert tokens < 700, (
            f"Agent instructions are ~{tokens} tokens. Target <700."
        )

    def test_skill_instructions_under_600_tokens(self):
        """Skill instructions are loaded into context whenever the skill
        triggers. Keep them concise."""
        text = _read_text("skills/verify-claim/SKILL.md")
        tokens = _approx_tokens(text)
        assert tokens < 600, (
            f"Skill instructions are ~{tokens} tokens. Target <600 to "
            "minimize context pollution."
        )

    def test_command_instructions_under_600_tokens(self):
        """Command instructions need error handling docs too."""
        text = _read_text("commands/verify.md")
        tokens = _approx_tokens(text)
        assert tokens < 600, (
            f"Command instructions are ~{tokens} tokens. Target <600."
        )

    def test_total_instruction_tokens_under_2000(self):
        """Sum of all instruction files should stay under 2000 tokens.
        This is the worst-case token load if all are active simultaneously."""
        files = [
            "agents/vvuq-verifier.md",
            "commands/verify.md",
            "skills/verify-claim/SKILL.md",
        ]
        total = sum(_approx_tokens(_read_text(f)) for f in files)
        assert total < 2000, (
            f"Total instruction tokens ~{total}. Target <2000 to keep "
            "plugin lightweight in the user's context window."
        )

    @pytest.mark.xfail(reason="Each component must be self-contained for independent use")
    def test_no_duplicate_verdict_tables(self):
        """The verdict table (verified/flagged/uncertain/unverifiable) appears
        in multiple files. Duplicated reference material wastes tokens —
        it should live in ONE canonical location and be referenced elsewhere."""
        verdict_pattern = re.compile(
            r"verified.*flagged.*uncertain.*unverifiable",
            re.DOTALL | re.IGNORECASE,
        )
        files_with_verdict_table = []
        for name in ("agents/vvuq-verifier.md", "commands/verify.md",
                      "skills/verify-claim/SKILL.md"):
            text = _read_text(name)
            if verdict_pattern.search(text):
                files_with_verdict_table.append(name)

        assert len(files_with_verdict_table) <= 1, (
            f"Verdict reference table duplicated in {len(files_with_verdict_table)} "
            f"files: {files_with_verdict_table}. "
            "Keep it in one place (e.g., the command) and remove from others "
            f"to save ~{len(files_with_verdict_table) - 1} x 50 tokens."
        )


# ===========================================================================
# 7. Skill trigger specificity — false positive risk
# ===========================================================================

class TestSkillTriggerSpecificity:

    def test_skill_description_not_too_broad(self):
        """The skill description determines when Claude auto-triggers it.
        Overly broad descriptions cause false triggers on normal conversation,
        wasting MCP calls and user tokens."""
        text = _read_text("skills/verify-claim/SKILL.md")
        # Extract YAML frontmatter description
        match = re.search(
            r"^description:\s*(.+?)(?=\n\w+:|\n---)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        assert match, "Skill has no description in frontmatter."
        desc = match.group(1).strip()

        # Check for overly generic trigger phrases that match normal conversation
        broad_phrases = [
            "any claim",
            "all claims",
            "every claim",
            "whenever",
            "any statement",
            "all statements",
        ]
        found = [p for p in broad_phrases if p.lower() in desc.lower()]
        assert not found, (
            f"Skill description contains overly broad trigger phrases: {found}. "
            "This will cause false triggers on normal conversation. "
            "Be more specific about STEM/scientific context."
        )

    def test_skill_description_mentions_stem_domain(self):
        """Skill description should explicitly mention STEM/scientific domain
        to avoid triggering on non-technical claims."""
        text = _read_text("skills/verify-claim/SKILL.md")
        match = re.search(
            r"^description:\s*(.+?)(?=\n\w+:|\n---)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        desc = match.group(1).strip().lower()

        domain_terms = ["stem", "scientific", "physics", "engineering",
                        "mathematical", "ieee", "standards"]
        found = [t for t in domain_terms if t in desc]
        assert len(found) >= 2, (
            f"Skill description only mentions {found} domain terms. "
            "Include at least 2 STEM-specific terms to reduce false triggers "
            "on non-technical claims."
        )


# ===========================================================================
# 8. Unnecessary files — files that don't contribute to plugin function
# ===========================================================================

class TestUnnecessaryFiles:

    def test_no_binary_files_in_distribution(self):
        """The distributed plugin (config + markdown) should have zero binary files."""
        binary_extensions = {
            ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2",
            ".ttf", ".otf", ".zip", ".tar", ".gz", ".pdf", ".exe", ".dll",
            ".so", ".dylib", ".pyc", ".pyo",
        }
        binaries = [
            p for p in _distribution_files()
            if p.suffix.lower() in binary_extensions
        ]
        assert not binaries, (
            f"Binary files found in distribution: "
            f"{[str(b.relative_to(PLUGIN_ROOT)) for b in binaries]}. "
            "A config-only plugin should have no binaries."
        )

    def test_no_test_files_in_distribution_root(self):
        """Test files should be in tests/ directory, not scattered in plugin root."""
        test_files = [
            p for p in _distribution_files()
            if p.name.startswith("test_")
        ]
        assert not test_files, (
            f"Test files in distribution tree: "
            f"{[str(t.relative_to(PLUGIN_ROOT)) for t in test_files]}"
        )
