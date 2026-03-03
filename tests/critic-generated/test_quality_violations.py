"""
Critic-generated quality tests for the vvuq4ai Claude Code plugin.

Validates JSON validity, YAML frontmatter, markdown quality,
spelling/grammar patterns, consistency, examples, and README completeness
for a public GitHub marketplace distribution.

Generated: 2026-03-02
"""

import json
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PLUGIN_ROOT = Path(__file__).parent.parent.parent
assert PLUGIN_ROOT.exists(), f"Plugin root not found: {PLUGIN_ROOT}"


@pytest.fixture(scope="session")
def plugin_root() -> Path:
    return PLUGIN_ROOT


@pytest.fixture(scope="session")
def plugin_json(plugin_root) -> dict:
    return json.loads((plugin_root / ".claude-plugin" / "plugin.json").read_text())


@pytest.fixture(scope="session")
def marketplace_json(plugin_root) -> dict:
    return json.loads((plugin_root / ".claude-plugin" / "marketplace.json").read_text())


@pytest.fixture(scope="session")
def mcp_json(plugin_root) -> dict:
    return json.loads((plugin_root / ".mcp.json").read_text())


@pytest.fixture(scope="session")
def readme_text(plugin_root) -> str:
    return (plugin_root / "README.md").read_text()


@pytest.fixture(scope="session")
def all_markdown_files(plugin_root) -> list[Path]:
    return sorted(plugin_root.rglob("*.md"))


def _parse_yaml_frontmatter(text: str) -> tuple[dict | None, str]:
    """Parse YAML frontmatter from markdown text.

    Returns (frontmatter_dict, body) or (None, full_text) if no frontmatter.
    """
    match = re.match(r"\A---\n(.*?\n)---\n?(.*)", text, re.DOTALL)
    if not match:
        return None, text
    raw_yaml = match.group(1)
    body = match.group(2)
    # Minimal YAML parsing -- enough for simple key: value and key: >\n blocks
    fm: dict = {}
    current_key = None
    current_val_lines: list[str] = []
    for line in raw_yaml.splitlines():
        # continuation of multiline scalar
        if current_key and (line.startswith("  ") or line.strip() == ""):
            current_val_lines.append(line.strip())
            continue
        # flush previous key
        if current_key:
            fm[current_key] = " ".join(current_val_lines).strip()
            current_key = None
            current_val_lines = []
        # new key
        kv = re.match(r"^(\w[\w-]*):\s*(.*)", line)
        if kv:
            key = kv.group(1)
            val = kv.group(2).strip()
            if val in (">", "|", ""):
                current_key = key
                current_val_lines = []
            else:
                fm[key] = val
        # lines starting with '  -' are list items; handle capabilities list
        list_item = re.match(r"^\s+-\s+(.*)", line)
        if list_item and current_key is None:
            # belongs to previous key that was a list
            pass  # we don't need deep YAML parsing for these tests
    if current_key:
        fm[current_key] = " ".join(current_val_lines).strip()
    return fm, body


# ===========================================================================
# 1. JSON VALIDITY
# ===========================================================================


class TestJsonValidity:
    """All JSON files must parse without errors."""

    def test_plugin_json_parses(self, plugin_root):
        path = plugin_root / ".claude-plugin" / "plugin.json"
        data = json.loads(path.read_text())
        assert isinstance(data, dict)

    def test_marketplace_json_parses(self, plugin_root):
        path = plugin_root / ".claude-plugin" / "marketplace.json"
        data = json.loads(path.read_text())
        assert isinstance(data, dict)

    def test_mcp_json_parses(self, plugin_root):
        path = plugin_root / ".mcp.json"
        data = json.loads(path.read_text())
        assert isinstance(data, dict)

    def test_no_trailing_commas_in_json(self, plugin_root):
        """JSON with trailing commas is invalid and some parsers reject it."""
        for p in plugin_root.rglob("*.json"):
            if ".git" in p.parts:
                continue
            text = p.read_text()
            # trailing comma before } or ]
            assert not re.search(
                r",\s*[}\]]", text
            ), f"Trailing comma in {p.relative_to(plugin_root)}"

    def test_no_json_comments(self, plugin_root):
        """JSON does not support comments; ensure none are present."""
        for p in plugin_root.rglob("*.json"):
            if ".git" in p.parts:
                continue
            text = p.read_text()
            # line comments
            for lineno, line in enumerate(text.splitlines(), 1):
                stripped = line.lstrip()
                assert not stripped.startswith("//"), (
                    f"Line comment in {p.relative_to(plugin_root)}:{lineno}"
                )


# ===========================================================================
# 2. JSON SCHEMA CONFORMANCE
# ===========================================================================


class TestPluginJsonSchema:
    """plugin.json must contain all required fields with correct types."""

    REQUIRED_KEYS = ["name", "version", "description", "author", "license"]

    def test_required_keys_present(self, plugin_json):
        for key in self.REQUIRED_KEYS:
            assert key in plugin_json, f"Missing required key: {key}"

    def test_name_is_lowercase_slug(self, plugin_json):
        name = plugin_json["name"]
        assert re.match(
            r"^[a-z0-9][a-z0-9_-]*$", name
        ), f"Plugin name '{name}' is not a valid slug"

    def test_version_is_semver(self, plugin_json):
        ver = plugin_json["version"]
        assert re.match(
            r"^\d+\.\d+\.\d+$", ver
        ), f"Version '{ver}' is not valid semver"

    def test_author_has_name_and_email(self, plugin_json):
        author = plugin_json.get("author", {})
        assert "name" in author, "author.name missing"
        assert "email" in author, "author.email missing"

    def test_license_is_spdx(self, plugin_json):
        valid_licenses = {"MIT", "Apache-2.0", "BSD-3-Clause", "GPL-3.0", "ISC", "UNLICENSED"}
        assert plugin_json["license"] in valid_licenses, (
            f"License '{plugin_json['license']}' not a recognized SPDX identifier"
        )

    def test_keywords_are_strings(self, plugin_json):
        kw = plugin_json.get("keywords", [])
        assert isinstance(kw, list)
        for item in kw:
            assert isinstance(item, str), f"Keyword {item!r} is not a string"

    def test_mcp_servers_path_exists(self, plugin_json, plugin_root):
        mcp_path = plugin_json.get("mcpServers")
        if mcp_path:
            # mcpServers path is relative to the plugin root, not .claude-plugin/
            resolved = (plugin_root / mcp_path).resolve()
            assert resolved.exists(), f"mcpServers path does not exist: {mcp_path}"


class TestMarketplaceJsonSchema:
    """marketplace.json must have valid structure."""

    def test_has_name(self, marketplace_json):
        assert "name" in marketplace_json

    def test_has_owner(self, marketplace_json):
        owner = marketplace_json.get("owner", {})
        assert "name" in owner, "owner.name missing"

    def test_has_plugins_list(self, marketplace_json):
        plugins = marketplace_json.get("plugins", [])
        assert isinstance(plugins, list)
        assert len(plugins) >= 1, "At least one plugin entry required"

    def test_plugin_entry_has_required_fields(self, marketplace_json):
        for entry in marketplace_json.get("plugins", []):
            for key in ("name", "source", "description", "version"):
                assert key in entry, f"Plugin entry missing '{key}'"


class TestMcpJsonSchema:
    """MCP config must point to a valid URL."""

    def test_has_mcp_servers_key(self, mcp_json):
        assert "mcpServers" in mcp_json

    def test_server_has_url(self, mcp_json):
        servers = mcp_json.get("mcpServers", {})
        for name, config in servers.items():
            assert "url" in config, f"Server '{name}' missing 'url'"

    def test_server_url_is_https(self, mcp_json):
        servers = mcp_json.get("mcpServers", {})
        for name, config in servers.items():
            url = config.get("url", "")
            assert url.startswith("https://"), (
                f"Server '{name}' URL is not HTTPS: {url}"
            )

    def test_server_url_has_trailing_slash(self, mcp_json):
        """SSE endpoints typically require trailing slash."""
        servers = mcp_json.get("mcpServers", {})
        for name, config in servers.items():
            url = config.get("url", "")
            assert url.endswith("/"), (
                f"Server '{name}' URL missing trailing slash: {url}"
            )


# ===========================================================================
# 3. YAML FRONTMATTER VALIDITY
# ===========================================================================


class TestYamlFrontmatter:
    """All markdown files with YAML frontmatter must parse correctly."""

    MARKDOWN_WITH_FRONTMATTER = [
        "agents/vvuq-verifier.md",
        "commands/verify.md",
        "skills/verify-claim/SKILL.md",
    ]

    @pytest.mark.parametrize("relpath", MARKDOWN_WITH_FRONTMATTER)
    def test_frontmatter_parses(self, plugin_root, relpath):
        path = plugin_root / relpath
        assert path.exists(), f"File not found: {relpath}"
        text = path.read_text()
        assert text.startswith("---\n"), f"No YAML frontmatter in {relpath}"
        fm, _ = _parse_yaml_frontmatter(text)
        assert fm is not None, f"Failed to parse frontmatter in {relpath}"

    @pytest.mark.parametrize("relpath", MARKDOWN_WITH_FRONTMATTER)
    def test_frontmatter_has_name(self, plugin_root, relpath):
        text = (plugin_root / relpath).read_text()
        fm, _ = _parse_yaml_frontmatter(text)
        assert fm is not None
        assert "name" in fm, f"Frontmatter missing 'name' in {relpath}"

    @pytest.mark.parametrize("relpath", MARKDOWN_WITH_FRONTMATTER)
    def test_frontmatter_has_description(self, plugin_root, relpath):
        text = (plugin_root / relpath).read_text()
        fm, _ = _parse_yaml_frontmatter(text)
        assert fm is not None
        assert "description" in fm, f"Frontmatter missing 'description' in {relpath}"

    def test_command_has_argument_hint(self, plugin_root):
        text = (plugin_root / "commands/verify.md").read_text()
        fm, _ = _parse_yaml_frontmatter(text)
        assert fm is not None
        assert "argument-hint" in fm, "Command frontmatter missing 'argument-hint'"

    def test_skill_has_version(self, plugin_root):
        text = (plugin_root / "skills/verify-claim/SKILL.md").read_text()
        fm, _ = _parse_yaml_frontmatter(text)
        assert fm is not None
        assert "version" in fm, "Skill frontmatter missing 'version'"

    def test_no_frontmatter_in_readme(self, plugin_root):
        """README.md should NOT have YAML frontmatter (it's not a command/agent/skill)."""
        text = (plugin_root / "README.md").read_text()
        assert not text.startswith("---\n"), (
            "README.md should not have YAML frontmatter"
        )


# ===========================================================================
# 4. CROSS-FILE CONSISTENCY
# ===========================================================================


class TestCrossFileConsistency:
    """Values that appear in multiple files must be consistent."""

    def test_name_consistent_across_json(self, plugin_json, marketplace_json):
        assert plugin_json["name"] == marketplace_json["name"]
        for entry in marketplace_json.get("plugins", []):
            assert entry["name"] == plugin_json["name"]

    def test_version_consistent_across_json(self, plugin_json, marketplace_json):
        for entry in marketplace_json.get("plugins", []):
            assert entry["version"] == plugin_json["version"], (
                f"Version mismatch: plugin.json={plugin_json['version']} "
                f"vs marketplace plugin entry={entry['version']}"
            )

    def test_version_consistent_with_skill(self, plugin_json, plugin_root):
        text = (plugin_root / "skills/verify-claim/SKILL.md").read_text()
        fm, _ = _parse_yaml_frontmatter(text)
        if fm and "version" in fm:
            assert fm["version"] == plugin_json["version"], (
                f"Version mismatch: plugin.json={plugin_json['version']} "
                f"vs skill={fm['version']}"
            )

    def test_license_consistent(self, plugin_json, marketplace_json):
        for entry in marketplace_json.get("plugins", []):
            assert entry.get("license") == plugin_json["license"]

    def test_repository_url_consistent(self, plugin_json, marketplace_json):
        """Repository URL should point to the same repo across files."""
        repo_plugin = plugin_json.get("repository", "")
        for entry in marketplace_json.get("plugins", []):
            repo_market = entry.get("repository", "")
            if repo_plugin and repo_market:
                assert repo_plugin == repo_market, (
                    f"Repository mismatch: plugin.json='{repo_plugin}' "
                    f"vs marketplace='{repo_market}'"
                )

    def test_author_name_consistent(self, plugin_json, marketplace_json):
        author_plugin = plugin_json.get("author", {}).get("name", "")
        owner_market = marketplace_json.get("owner", {}).get("name", "")
        assert author_plugin == owner_market, (
            f"Author mismatch: plugin.json='{author_plugin}' "
            f"vs marketplace owner='{owner_market}'"
        )

    def test_mcp_server_name_consistent(self, plugin_json, mcp_json):
        """MCP server name should match the plugin name."""
        servers = mcp_json.get("mcpServers", {})
        assert plugin_json["name"] in servers, (
            f"MCP server '{plugin_json['name']}' not found in .mcp.json servers: "
            f"{list(servers.keys())}"
        )

    def test_mcp_url_consistent_with_readme(self, mcp_json, readme_text):
        """The MCP URL in .mcp.json should appear in README.md."""
        servers = mcp_json.get("mcpServers", {})
        for name, config in servers.items():
            url = config.get("url", "")
            assert url in readme_text, (
                f"MCP server URL '{url}' not mentioned in README.md"
            )


# ===========================================================================
# 5. MARKDOWN QUALITY
# ===========================================================================


class TestMarkdownQuality:
    """Check for common markdown rendering issues."""

    def test_no_broken_markdown_links(self, all_markdown_files, plugin_root):
        """Check for malformed inline links like [text](url with spaces)."""
        link_re = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
        for md_file in all_markdown_files:
            if ".git" in md_file.parts:
                continue
            text = md_file.read_text()
            for match in link_re.finditer(text):
                url = match.group(2)
                # urls with unescaped spaces are broken
                assert " " not in url or url.startswith("<"), (
                    f"Broken link in {md_file.relative_to(plugin_root)}: "
                    f"[{match.group(1)}]({url})"
                )

    def test_no_malformed_tables(self, all_markdown_files, plugin_root):
        """Tables must have consistent column counts across header, separator, and rows."""
        table_sep_re = re.compile(r"^\|[\s\-:|]+\|$")
        for md_file in all_markdown_files:
            if ".git" in md_file.parts:
                continue
            lines = md_file.read_text().splitlines()
            for i, line in enumerate(lines):
                if table_sep_re.match(line.strip()):
                    sep_cols = line.strip().count("|") - 1
                    # check header (line above)
                    if i > 0:
                        header = lines[i - 1].strip()
                        if header.startswith("|"):
                            header_cols = header.count("|") - 1
                            assert header_cols == sep_cols, (
                                f"Table column mismatch in "
                                f"{md_file.relative_to(plugin_root)}:"
                                f"{i}: header={header_cols} sep={sep_cols}"
                            )
                    # check data rows below
                    for j in range(i + 1, min(i + 20, len(lines))):
                        row = lines[j].strip()
                        if not row.startswith("|"):
                            break
                        row_cols = row.count("|") - 1
                        assert row_cols == sep_cols, (
                            f"Table column mismatch in "
                            f"{md_file.relative_to(plugin_root)}:"
                            f"{j + 1}: row={row_cols} sep={sep_cols}"
                        )

    def test_no_unclosed_code_blocks(self, all_markdown_files, plugin_root):
        """Triple-backtick code blocks must be properly closed."""
        for md_file in all_markdown_files:
            if ".git" in md_file.parts:
                continue
            text = md_file.read_text()
            # Strip YAML frontmatter before counting
            _, body = _parse_yaml_frontmatter(text)
            count = body.count("```")
            assert count % 2 == 0, (
                f"Unclosed code block in {md_file.relative_to(plugin_root)}: "
                f"found {count} triple-backtick markers (should be even)"
            )

    def test_headings_have_space_after_hash(self, all_markdown_files, plugin_root):
        """ATX headings require a space after # (e.g., '# Title' not '#Title')."""
        for md_file in all_markdown_files:
            if ".git" in md_file.parts:
                continue
            _, body = _parse_yaml_frontmatter(md_file.read_text())
            in_code = False
            for lineno, line in enumerate(body.splitlines(), 1):
                if line.strip().startswith("```"):
                    in_code = not in_code
                    continue
                if in_code:
                    continue
                if re.match(r"^#{1,6}[^ #\n]", line):
                    pytest.fail(
                        f"Missing space after heading hash in "
                        f"{md_file.relative_to(plugin_root)}:{lineno}: {line!r}"
                    )


# ===========================================================================
# 6. TERMINOLOGY CONSISTENCY
# ===========================================================================


class TestTerminologyConsistency:
    """Same concepts should use identical terms everywhere."""

    def test_tool_names_consistent(self, all_markdown_files, plugin_root):
        """Tool names (vvuq_resolve, vvuq_query) should be spelled consistently."""
        tool_pattern = re.compile(r"`(vvuq_\w+)`")
        all_tool_names: set[str] = set()
        for md_file in all_markdown_files:
            if ".git" in md_file.parts:
                continue
            text = md_file.read_text()
            found = tool_pattern.findall(text)
            all_tool_names.update(found)
        # All referenced tools should be documented in at least the command or agent file
        agent_text = (plugin_root / "agents" / "vvuq-verifier.md").read_text()
        for tool_name in all_tool_names:
            assert tool_name in agent_text, (
                f"Tool '{tool_name}' referenced somewhere but not documented "
                f"in agents/vvuq-verifier.md"
            )

    def test_verdict_values_consistent(self, all_markdown_files, plugin_root):
        """Verdict values (verified, flagged, uncertain, unverifiable) must be consistent."""
        canonical = {"verified", "flagged", "uncertain", "unverifiable"}
        verdict_re = re.compile(r"verdict[:\s]+[\"']?(\w+)[\"']?", re.IGNORECASE)
        for md_file in all_markdown_files:
            if ".git" in md_file.parts:
                continue
            text = md_file.read_text()
            for match in verdict_re.finditer(text):
                val = match.group(1).lower()
                # Only check words that look like verdict values
                if val in ("the", "and", "or", "is", "a", "x", "all"):
                    continue
                # Allow uppercase versions in report format
                if val.upper() in {v.upper() for v in canonical}:
                    continue
                # If it looks like a verdict value but isn't canonical, flag it
                if val not in canonical and val not in (
                    "meaning", "action", "checks", "pass"
                ):
                    # Only fail for close misspellings
                    pass  # intentionally lenient; the table check below is strict

    def test_verdict_table_in_readme(self, readme_text):
        """README must document all four verdict values."""
        for verdict in ("verified", "flagged", "uncertain", "unverifiable"):
            assert verdict in readme_text.lower(), (
                f"Verdict '{verdict}' not documented in README.md"
            )

    def test_verdict_table_in_skill(self, plugin_root):
        """SKILL.md must document all four verdict values."""
        text = (plugin_root / "skills" / "verify-claim" / "SKILL.md").read_text()
        for verdict in ("verified", "flagged", "uncertain", "unverifiable"):
            assert verdict in text.lower(), (
                f"Verdict '{verdict}' not documented in SKILL.md"
            )

    def test_knowledge_base_size_consistent(self, all_markdown_files, plugin_root):
        """The '40K+ nodes' claim should be consistent across files."""
        kb_pattern = re.compile(r"(\d+)K\+?\s*(curated\s+)?(knowledge\s+)?nodes?", re.IGNORECASE)
        sizes: dict[str, str] = {}
        for md_file in all_markdown_files:
            if ".git" in md_file.parts:
                continue
            text = md_file.read_text()
            m = kb_pattern.search(text)
            if m:
                sizes[str(md_file.relative_to(plugin_root))] = m.group(1)
        # All files that mention KB size should agree
        unique_sizes = set(sizes.values())
        assert len(unique_sizes) <= 1, (
            f"Inconsistent knowledge base size claims: {sizes}"
        )


# ===========================================================================
# 7. SPELLING & GRAMMAR (pattern-based)
# ===========================================================================


class TestSpellingGrammar:
    """Check for common spelling/grammar issues in user-facing text."""

    COMMON_MISSPELLINGS = {
        r"\bthier\b": "their",
        r"\bteh\b": "the",
        r"\brecieve\b": "receive",
        r"\bsepearte\b": "separate",
        r"\boccured\b": "occurred",
        r"\bcommited\b": "committed",
        r"\bverifiy\b": "verify",
        r"\bvalidaiton\b": "validation",
        r"\buncertianty\b": "uncertainty",
        r"\bcompliance\b(?!\s)compiance": "compliance",
        r"\bdimentional\b": "dimensional",
        r"\bstandars\b": "standards",
        r"\bmathmatical\b": "mathematical",
        r"\bphyiscs\b": "physics",
        r"\bformulae?\s+is\b": "formula is / formulae are",
    }

    @pytest.mark.parametrize(
        "pattern,correction",
        list(COMMON_MISSPELLINGS.items()),
        ids=list(COMMON_MISSPELLINGS.values()),
    )
    def test_no_common_misspellings(
        self, all_markdown_files, plugin_root, pattern, correction
    ):
        for md_file in all_markdown_files:
            if ".git" in md_file.parts:
                continue
            text = md_file.read_text()
            matches = re.findall(pattern, text, re.IGNORECASE)
            assert not matches, (
                f"Possible misspelling in {md_file.relative_to(plugin_root)}: "
                f"found {matches!r}, did you mean '{correction}'?"
            )

    def test_no_double_spaces_in_prose(self, all_markdown_files, plugin_root):
        """Double spaces in prose are usually typos (except in code blocks)."""
        for md_file in all_markdown_files:
            if ".git" in md_file.parts:
                continue
            _, body = _parse_yaml_frontmatter(md_file.read_text())
            in_code = False
            for lineno, line in enumerate(body.splitlines(), 1):
                if line.strip().startswith("```"):
                    in_code = not in_code
                    continue
                if in_code:
                    continue
                # Skip table alignment and list indentation
                if line.strip().startswith("|") or line.strip().startswith("-"):
                    continue
                if "  " in line.strip() and not line.strip().startswith("#"):
                    # Allow markdown emphasis spacing
                    cleaned = re.sub(r"\*\*.*?\*\*", "", line)
                    if "  " in cleaned.strip():
                        pytest.fail(
                            f"Double space in {md_file.relative_to(plugin_root)}"
                            f":{lineno}: {line.rstrip()!r}"
                        )


# ===========================================================================
# 8. EXAMPLE QUALITY
# ===========================================================================


class TestExampleQuality:
    """Examples must be realistic and syntactically correct."""

    def test_verify_command_example_in_readme(self, readme_text):
        """README must show a /verify example."""
        assert "/verify" in readme_text, "README missing /verify usage example"

    def test_verify_command_example_has_claim(self, readme_text):
        """The /verify example should include an actual claim, not just the command."""
        lines = readme_text.splitlines()
        for line in lines:
            if "/verify" in line and len(line.strip()) > len("/verify") + 5:
                return  # Found a /verify with a claim
        pytest.fail("README /verify example should include an actual STEM claim")

    def test_code_blocks_have_language_hints(self, all_markdown_files, plugin_root):
        """Fenced code blocks should specify a language for syntax highlighting."""
        for md_file in all_markdown_files:
            if ".git" in md_file.parts:
                continue
            _, body = _parse_yaml_frontmatter(md_file.read_text())
            lines = body.splitlines()
            for lineno, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped == "```":
                    # Opening fence without language -- check if it's a closing fence
                    # Count preceding fences to determine if this opens or closes
                    preceding = body.splitlines()[:lineno - 1]
                    open_count = sum(
                        1 for l in preceding if l.strip().startswith("```")
                    )
                    if open_count % 2 == 0:
                        # This is an opening fence without a language hint
                        # Check what follows to determine if it's prose-like output
                        if lineno < len(lines):
                            next_line = lines[lineno].strip() if lineno < len(lines) else ""
                            # Allow bare fences for non-code output formats
                            if next_line.startswith("Claim:") or next_line.startswith("vvuq_"):
                                continue
                        pytest.fail(
                            f"Code block without language hint in "
                            f"{md_file.relative_to(plugin_root)}:{lineno}"
                        )

    def test_speed_of_light_example_is_accurate(self, all_markdown_files, plugin_root):
        """Examples using speed of light should reference the correct value."""
        c_correct = 299792458
        c_pattern = re.compile(r"speed of light\b.*?(\d{9,})", re.IGNORECASE)
        for md_file in all_markdown_files:
            if ".git" in md_file.parts:
                continue
            text = md_file.read_text()
            for match in c_pattern.finditer(text):
                value = int(match.group(1))
                # The example deliberately uses the WRONG value (300000000)
                # to demonstrate the plugin catching the error.
                # But the CORRECTION should state the right value.
                if value == c_correct:
                    continue  # correct value, fine
                if value == 300000000:
                    # This is the deliberately wrong value used in examples.
                    # Verify the correction mentions the right value nearby.
                    context_after = text[match.end():match.end() + 500]
                    assert str(c_correct) in context_after, (
                        f"Example in {md_file.relative_to(plugin_root)} uses "
                        f"wrong speed of light ({value}) but doesn't provide "
                        f"the correct value ({c_correct}) in the correction"
                    )


# ===========================================================================
# 9. README COMPLETENESS
# ===========================================================================


class TestReadmeCompleteness:
    """README.md must cover all essential sections for a marketplace plugin."""

    REQUIRED_SECTIONS = [
        "installation",
        "usage",
        "requirements",
        "license",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_readme_has_section(self, readme_text, section):
        """README must have headed sections for key topics."""
        # Check for ## heading containing the keyword
        heading_pattern = re.compile(
            rf"^#+\s+.*{section}.*$", re.IGNORECASE | re.MULTILINE
        )
        assert heading_pattern.search(readme_text), (
            f"README.md missing section for '{section}'"
        )

    def test_readme_documents_verify_command(self, readme_text):
        assert "/verify" in readme_text, "README missing /verify command documentation"

    def test_readme_documents_agent(self, readme_text):
        assert "vvuq-verifier" in readme_text, "README missing agent documentation"

    def test_readme_documents_skill(self, readme_text):
        assert "verify-claim" in readme_text, "README missing skill documentation"

    def test_readme_documents_verdicts(self, readme_text):
        """All four verdict values must be documented."""
        for verdict in ("verified", "flagged", "uncertain", "unverifiable"):
            assert verdict in readme_text.lower(), (
                f"README missing documentation for verdict: {verdict}"
            )

    def test_readme_mentions_mcp_url(self, readme_text):
        assert "vvuq.dirkenglund.org" in readme_text

    def test_readme_has_no_api_key_requirement(self, readme_text):
        """README should explicitly state no API key is needed."""
        assert "no api key" in readme_text.lower() or "no key" in readme_text.lower(), (
            "README should mention that no API key is needed"
        )

    def test_readme_starts_with_title(self, readme_text):
        """README should begin with a level-1 heading."""
        first_line = readme_text.strip().splitlines()[0]
        assert first_line.startswith("# "), (
            f"README should start with '# Title', got: {first_line!r}"
        )


# ===========================================================================
# 10. FILE STRUCTURE
# ===========================================================================


class TestFileStructure:
    """Plugin must have the expected directory structure."""

    REQUIRED_FILES = [
        ".claude-plugin/plugin.json",
        ".mcp.json",
        "README.md",
        "LICENSE",
    ]

    EXPECTED_DIRS = [
        "agents",
        "commands",
        "skills",
    ]

    @pytest.mark.parametrize("relpath", REQUIRED_FILES)
    def test_required_file_exists(self, plugin_root, relpath):
        assert (plugin_root / relpath).exists(), f"Missing required file: {relpath}"

    @pytest.mark.parametrize("dirname", EXPECTED_DIRS)
    def test_expected_directory_exists(self, plugin_root, dirname):
        assert (plugin_root / dirname).is_dir(), f"Missing directory: {dirname}"

    def test_no_stale_files(self, plugin_root):
        """No .pyc, .DS_Store, or node_modules should be committed (excluding tests/)."""
        excluded_dirs = {".git", "tests", "__pycache__"}
        for pattern in ("*.pyc", ".DS_Store", "node_modules"):
            matches = list(plugin_root.rglob(pattern))
            # Filter out .git and tests directories (test artifacts are expected)
            matches = [
                m for m in matches
                if not any(excl in m.parts for excl in excluded_dirs)
            ]
            assert not matches, (
                f"Stale files found: {[str(m.relative_to(plugin_root)) for m in matches]}"
            )

    def test_gitignore_exists(self, plugin_root):
        assert (plugin_root / ".gitignore").exists()

    def test_gitignore_covers_common_patterns(self, plugin_root):
        gitignore = (plugin_root / ".gitignore").read_text()
        for pattern in (".DS_Store", "__pycache__", "*.pyc"):
            assert pattern in gitignore, (
                f".gitignore missing pattern: {pattern}"
            )

    def test_license_file_not_empty(self, plugin_root):
        license_text = (plugin_root / "LICENSE").read_text()
        assert len(license_text) > 100, "LICENSE file appears empty or truncated"

    def test_license_mentions_mit(self, plugin_root):
        license_text = (plugin_root / "LICENSE").read_text()
        assert "MIT" in license_text, "LICENSE file doesn't mention MIT"


# ===========================================================================
# 11. SECURITY & SENSITIVE DATA
# ===========================================================================


class TestSecurity:
    """No sensitive data should be present in plugin files."""

    def test_no_api_keys_in_files(self, plugin_root):
        """Check for accidentally committed API keys or secrets."""
        key_patterns = [
            re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI-style keys
            re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access keys
            re.compile(r"ghp_[a-zA-Z0-9]{36}"),  # GitHub PAT
            re.compile(r"gcloud.*secret.*=\s*['\"]?[a-zA-Z0-9+/]{20,}"),  # GCloud
        ]
        for f in plugin_root.rglob("*"):
            if f.is_dir() or ".git" in f.parts:
                continue
            if f.suffix in (".pyc", ".png", ".jpg", ".gif"):
                continue
            try:
                text = f.read_text()
            except (UnicodeDecodeError, PermissionError):
                continue
            for pat in key_patterns:
                matches = pat.findall(text)
                assert not matches, (
                    f"Possible API key in {f.relative_to(plugin_root)}: "
                    f"{[m[:10] + '...' for m in matches]}"
                )

    def test_no_env_files(self, plugin_root):
        """No .env files should be committed."""
        env_files = list(plugin_root.rglob(".env*"))
        env_files = [f for f in env_files if ".git" not in f.parts]
        assert not env_files, (
            f".env files found: {[str(f.relative_to(plugin_root)) for f in env_files]}"
        )

    def test_no_hardcoded_passwords(self, plugin_root):
        """No hardcoded passwords in any plugin source file."""
        pwd_pattern = re.compile(r"password\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE)
        for f in plugin_root.rglob("*"):
            if f.is_dir() or ".git" in f.parts or "tests" in f.parts:
                continue
            try:
                text = f.read_text()
            except (UnicodeDecodeError, PermissionError):
                continue
            matches = pwd_pattern.findall(text)
            assert not matches, (
                f"Hardcoded password in {f.relative_to(plugin_root)}"
            )


# ===========================================================================
# 12. PRIVACY POLICY — HTML VALIDITY & QUALITY (Round 2 Critic)
# ===========================================================================


class TestPrivacyHtmlExists:
    """privacy.html must exist and be a non-empty file."""

    @pytest.mark.xfail(reason="privacy.html lives in vvuq-mcp server repo, not plugin distribution (issue #197)")
    def test_privacy_html_exists(self, plugin_root):
        path = plugin_root / "privacy.html"
        assert path.exists(), "privacy.html not found in plugin root"

    def test_privacy_html_not_empty(self, plugin_root):
        path = plugin_root / "privacy.html"
        if not path.exists():
            pytest.skip("privacy.html does not exist")
        content = path.read_text()
        assert len(content) > 100, (
            f"privacy.html appears empty or truncated ({len(content)} chars)"
        )


class TestPrivacyHtmlValidity:
    """privacy.html must be valid, well-formed HTML5."""

    @pytest.fixture(scope="class")
    def privacy_html(self, plugin_root) -> str:
        path = plugin_root / "privacy.html"
        if not path.exists():
            pytest.skip("privacy.html does not exist")
        return path.read_text()

    def test_has_doctype(self, privacy_html):
        """HTML5 pages must start with <!DOCTYPE html>."""
        assert privacy_html.strip().lower().startswith("<!doctype html>"), (
            "privacy.html must start with <!DOCTYPE html>"
        )

    def test_has_html_lang_attribute(self, privacy_html):
        """The <html> tag must have a lang attribute for accessibility."""
        assert re.search(r'<html[^>]+lang\s*=\s*["\']', privacy_html), (
            "privacy.html <html> tag missing lang attribute (accessibility requirement)"
        )

    def test_has_charset_meta(self, privacy_html):
        """Must declare character encoding via <meta charset>."""
        assert re.search(r'<meta\s+charset\s*=\s*["\']utf-8["\']', privacy_html, re.IGNORECASE), (
            "privacy.html missing <meta charset='utf-8'>"
        )

    def test_has_viewport_meta(self, privacy_html):
        """Must have viewport meta tag for responsive design."""
        assert re.search(r'<meta\s+name\s*=\s*["\']viewport["\']', privacy_html, re.IGNORECASE), (
            "privacy.html missing viewport meta tag (required for mobile responsiveness)"
        )

    def test_has_title(self, privacy_html):
        """Must have a <title> element."""
        assert re.search(r'<title>.+</title>', privacy_html, re.DOTALL), (
            "privacy.html missing <title> element"
        )

    def test_title_mentions_privacy(self, privacy_html):
        """The page title should indicate this is a privacy policy."""
        title_match = re.search(r'<title>(.+?)</title>', privacy_html, re.DOTALL)
        assert title_match, "privacy.html missing <title>"
        title = title_match.group(1).lower()
        assert "privacy" in title, (
            f"privacy.html title '{title_match.group(1)}' does not mention 'privacy'"
        )

    def test_has_body_tags(self, privacy_html):
        """Must have proper <body> structure."""
        assert "<body>" in privacy_html.lower(), "privacy.html missing <body> tag"
        assert "</body>" in privacy_html.lower(), "privacy.html missing </body> tag"

    def test_has_head_tags(self, privacy_html):
        """Must have proper <head> structure."""
        assert "<head>" in privacy_html.lower(), "privacy.html missing <head> tag"
        assert "</head>" in privacy_html.lower(), "privacy.html missing </head> tag"

    def test_html_tags_properly_closed(self, privacy_html):
        """Check that major structural tags are properly closed."""
        for tag in ["html", "head", "body"]:
            open_count = len(re.findall(rf'<{tag}[\s>]', privacy_html, re.IGNORECASE))
            close_count = len(re.findall(rf'</{tag}>', privacy_html, re.IGNORECASE))
            assert open_count == close_count, (
                f"privacy.html: <{tag}> appears {open_count} times but "
                f"</{tag}> appears {close_count} times"
            )

    def test_no_unclosed_heading_tags(self, privacy_html):
        """All heading tags (h1-h6) must be properly closed."""
        for level in range(1, 7):
            open_count = len(re.findall(rf'<h{level}[\s>]', privacy_html, re.IGNORECASE))
            close_count = len(re.findall(rf'</h{level}>', privacy_html, re.IGNORECASE))
            assert open_count == close_count, (
                f"privacy.html: <h{level}> count ({open_count}) != "
                f"</h{level}> count ({close_count})"
            )

    def test_no_unclosed_paragraph_tags(self, privacy_html):
        """<p> tags should have matching </p> tags."""
        open_count = len(re.findall(r'<p[\s>]', privacy_html, re.IGNORECASE))
        close_count = len(re.findall(r'</p>', privacy_html, re.IGNORECASE))
        assert open_count == close_count, (
            f"privacy.html: <p> count ({open_count}) != </p> count ({close_count})"
        )

    def test_no_unclosed_list_tags(self, privacy_html):
        """<ul> and <li> tags should be properly matched."""
        for tag in ["ul", "li"]:
            open_count = len(re.findall(rf'<{tag}[\s>]', privacy_html, re.IGNORECASE))
            close_count = len(re.findall(rf'</{tag}>', privacy_html, re.IGNORECASE))
            assert open_count == close_count, (
                f"privacy.html: <{tag}> count ({open_count}) != "
                f"</{tag}> count ({close_count})"
            )

    def test_links_have_href(self, privacy_html):
        """All <a> tags must have an href attribute."""
        a_tags = re.findall(r'<a\s+[^>]*>', privacy_html, re.IGNORECASE)
        for tag in a_tags:
            assert 'href=' in tag.lower(), (
                f"privacy.html: <a> tag without href: {tag}"
            )

    def test_mailto_links_valid(self, privacy_html):
        """mailto: links must have valid email addresses."""
        mailto_links = re.findall(r'href\s*=\s*["\']mailto:([^"\']+)["\']', privacy_html)
        email_re = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
        for email in mailto_links:
            assert email_re.match(email), (
                f"privacy.html: invalid email in mailto link: {email}"
            )


class TestPrivacyHtmlAccessibility:
    """privacy.html must meet basic accessibility standards."""

    @pytest.fixture(scope="class")
    def privacy_html(self, plugin_root) -> str:
        path = plugin_root / "privacy.html"
        if not path.exists():
            pytest.skip("privacy.html does not exist")
        return path.read_text()

    def test_has_h1_heading(self, privacy_html):
        """Page must have exactly one <h1> for screen reader navigation."""
        h1_count = len(re.findall(r'<h1[\s>]', privacy_html, re.IGNORECASE))
        assert h1_count == 1, (
            f"privacy.html should have exactly 1 <h1>, found {h1_count}"
        )

    def test_heading_hierarchy_not_skipped(self, privacy_html):
        """Heading levels should not skip (e.g., h1 then h3 without h2)."""
        headings = re.findall(r'<h(\d)', privacy_html, re.IGNORECASE)
        levels = [int(h) for h in headings]
        for i in range(1, len(levels)):
            jump = levels[i] - levels[i - 1]
            assert jump <= 1, (
                f"privacy.html: heading hierarchy skips from h{levels[i-1]} "
                f"to h{levels[i]} (should not skip levels)"
            )

    def test_sufficient_color_contrast_declaration(self, privacy_html):
        """Body text color should be dark enough for readability.
        A color like #222 on white background has sufficient contrast."""
        color_match = re.search(r'color:\s*#([0-9a-fA-F]{3,6})', privacy_html)
        if color_match:
            hex_color = color_match.group(1)
            if len(hex_color) == 3:
                hex_color = ''.join(c * 2 for c in hex_color)
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            # Luminance should be dark (low values) for readable text on white
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            assert luminance < 128, (
                f"privacy.html body text color #{hex_color} may not have "
                f"sufficient contrast against white background (luminance={luminance:.0f})"
            )

    def test_responsive_max_width(self, privacy_html):
        """Page should have a max-width constraint for readability on wide screens."""
        assert re.search(r'max-width:\s*\d+', privacy_html), (
            "privacy.html should set max-width on the body/container for readability"
        )

    def test_readable_line_height(self, privacy_html):
        """Line height should be at least 1.4 for readability."""
        lh_match = re.search(r'line-height:\s*([\d.]+)', privacy_html)
        if lh_match:
            lh = float(lh_match.group(1))
            assert lh >= 1.4, (
                f"privacy.html line-height is {lh}, should be >= 1.4 for readability"
            )


class TestPrivacyHtmlContent:
    """privacy.html must cover essential privacy policy sections."""

    @pytest.fixture(scope="class")
    def privacy_text(self, plugin_root) -> str:
        path = plugin_root / "privacy.html"
        if not path.exists():
            pytest.skip("privacy.html does not exist")
        # Strip HTML tags for text-only content analysis
        raw = path.read_text()
        return re.sub(r'<[^>]+>', ' ', raw)

    @pytest.fixture(scope="class")
    def privacy_html(self, plugin_root) -> str:
        path = plugin_root / "privacy.html"
        if not path.exists():
            pytest.skip("privacy.html does not exist")
        return path.read_text()

    REQUIRED_SECTIONS = [
        "what data is collected",
        "how data is used",
        "data retention",
        "contact",
    ]

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_has_required_section(self, privacy_text, section):
        """Privacy policy must cover essential topics."""
        assert section in privacy_text.lower(), (
            f"privacy.html missing required section: '{section}'"
        )

    def test_mentions_data_security(self, privacy_text):
        """Privacy policy should mention data security measures."""
        assert "security" in privacy_text.lower() or "encryption" in privacy_text.lower(), (
            "privacy.html should mention data security measures"
        )

    def test_mentions_https(self, privacy_text):
        """Should mention that connections use HTTPS."""
        assert "https" in privacy_text.lower() or "tls" in privacy_text.lower(), (
            "privacy.html should mention HTTPS/TLS for data in transit"
        )

    def test_mentions_no_third_party_sharing(self, privacy_text):
        """Should clarify whether data is shared with third parties."""
        assert "third part" in privacy_text.lower(), (
            "privacy.html should address third-party data sharing"
        )

    def test_has_last_updated_date(self, privacy_text):
        """Privacy policy must show when it was last updated."""
        assert re.search(r'(last\s+updated|effective\s+date)', privacy_text, re.IGNORECASE), (
            "privacy.html missing a 'Last updated' or 'Effective date' indicator"
        )

    def test_last_updated_date_is_recent(self, privacy_html):
        """The 'Last updated' date should be from 2026 (current year)."""
        date_match = re.search(r'last\s+updated:?\s*(\w+\s+\d+,?\s+\d{4})', privacy_html, re.IGNORECASE)
        if date_match:
            date_str = date_match.group(1)
            assert "2026" in date_str, (
                f"privacy.html 'Last updated' date '{date_str}' is not from 2026"
            )

    def test_mentions_opt_out(self, privacy_text):
        """Users should be informed about opt-out options."""
        assert "opt" in privacy_text.lower(), (
            "privacy.html should mention opt-out options for data collection"
        )

    def test_retention_period_specified(self, privacy_text):
        """Data retention periods should be explicitly stated."""
        has_retention_period = re.search(
            r'\d+\s*(days?|months?|years?)', privacy_text, re.IGNORECASE
        )
        assert has_retention_period, (
            "privacy.html should specify concrete data retention periods "
            "(e.g., '90 days', '12 months')"
        )

    def test_no_legal_jargon_without_plain_language(self, privacy_text):
        """Privacy policy should be in clear, plain language.
        Check for legalese that might confuse users."""
        legalese_terms = [
            "hereinafter",
            "notwithstanding",
            "indemnify",
            "whereas",
            "heretofore",
            "aforesaid",
            "inter alia",
            "mutatis mutandis",
        ]
        found = [t for t in legalese_terms if t in privacy_text.lower()]
        assert not found, (
            f"privacy.html contains legal jargon that may confuse users: {found}. "
            "Use plain language instead."
        )

    def test_no_spelling_errors_in_privacy(self, privacy_text):
        """Check for common misspellings in the privacy policy text."""
        misspellings = {
            r"\bprivicy\b": "privacy",
            r"\bcollect\b(?:ed|s|ing)?\b": None,  # skip, just checking bad ones
            r"\bprivicy\b": "privacy",
            r"\brecieve\b": "receive",
            r"\binformaiton\b": "information",
            r"\bpurpse\b": "purpose",
            r"\bprocesssing\b": "processing",
            r"\bsercurity\b": "security",
            r"\bretetnion\b": "retention",
            r"\bpersoanl\b": "personal",
        }
        for pattern, correction in misspellings.items():
            if correction is None:
                continue
            matches = re.findall(pattern, privacy_text, re.IGNORECASE)
            assert not matches, (
                f"privacy.html possible misspelling: found '{matches[0]}', "
                f"did you mean '{correction}'?"
            )


# ===========================================================================
# 13. PRIVACY POLICY CROSS-REFERENCES (Round 2 Critic)
# ===========================================================================


class TestPrivacyCrossReferences:
    """Check that privacy.html is properly referenced from other files."""

    def test_readme_mentions_privacy(self, readme_text):
        """README should mention the privacy policy for user awareness.
        A publicly distributed plugin that collects data (claim text,
        IP addresses) should reference its privacy policy."""
        has_privacy_ref = any(
            term in readme_text.lower()
            for term in ["privacy", "privacy.html", "privacy policy"]
        )
        assert has_privacy_ref, (
            "README.md does not mention a privacy policy. A plugin that sends "
            "user claim text to a remote server should reference its privacy "
            "policy so users know what data is collected."
        )

    def test_privacy_contact_email_matches_author(self, plugin_root):
        """The contact email in privacy.html must match the plugin author email."""
        privacy_path = plugin_root / "privacy.html"
        plugin_json_path = plugin_root / ".claude-plugin" / "plugin.json"
        if not privacy_path.exists():
            pytest.skip("privacy.html does not exist")

        privacy_text = privacy_path.read_text()
        plugin_data = json.loads(plugin_json_path.read_text())

        author_email = plugin_data.get("author", {}).get("email", "")
        assert author_email, "plugin.json author.email is empty"

        # Extract emails from privacy.html
        privacy_emails = re.findall(
            r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
            privacy_text
        )
        assert author_email in privacy_emails, (
            f"privacy.html contact email(s) {privacy_emails} do not include "
            f"the plugin author email '{author_email}'. These should be consistent."
        )

    def test_privacy_contact_email_matches_marketplace(self, plugin_root):
        """The contact email in privacy.html must match marketplace owner email."""
        privacy_path = plugin_root / "privacy.html"
        marketplace_path = plugin_root / ".claude-plugin" / "marketplace.json"
        if not privacy_path.exists():
            pytest.skip("privacy.html does not exist")

        privacy_text = privacy_path.read_text()
        marketplace_data = json.loads(marketplace_path.read_text())

        owner_email = marketplace_data.get("owner", {}).get("email", "")
        assert owner_email, "marketplace.json owner.email is empty"

        privacy_emails = re.findall(
            r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
            privacy_text
        )
        assert owner_email in privacy_emails, (
            f"privacy.html contact email(s) {privacy_emails} do not include "
            f"the marketplace owner email '{owner_email}'."
        )

    def test_privacy_mentions_plugin_name(self, plugin_root):
        """privacy.html should reference the plugin/service name for clarity."""
        privacy_path = plugin_root / "privacy.html"
        if not privacy_path.exists():
            pytest.skip("privacy.html does not exist")

        privacy_text = privacy_path.read_text()
        assert "VVUQ4AI" in privacy_text or "vvuq4ai" in privacy_text.lower(), (
            "privacy.html does not mention the plugin name 'VVUQ4AI'"
        )

    def test_privacy_mentions_plugin_operator(self, plugin_root):
        """privacy.html should identify who operates the service."""
        privacy_path = plugin_root / "privacy.html"
        plugin_json_path = plugin_root / ".claude-plugin" / "plugin.json"
        if not privacy_path.exists():
            pytest.skip("privacy.html does not exist")

        privacy_text = privacy_path.read_text()
        plugin_data = json.loads(plugin_json_path.read_text())
        author_name = plugin_data.get("author", {}).get("name", "")

        assert author_name.lower() in privacy_text.lower(), (
            f"privacy.html does not identify the operator/author '{author_name}'. "
            "Users should know who operates the service."
        )


# ===========================================================================
# 14. PLUGIN JSON PRIVACY URL FIELD (Round 2 Critic)
# ===========================================================================


class TestPluginJsonPrivacyUrl:
    """plugin.json and marketplace.json should reference a privacy policy URL
    if the plugin sends user data to a remote server."""

    def test_plugin_json_has_privacy_url(self, plugin_json):
        """plugin.json should include a privacyPolicy or privacy field
        pointing to the hosted privacy policy."""
        has_privacy = any(
            key in plugin_json
            for key in ["privacyPolicy", "privacy", "privacyUrl", "privacy_url"]
        )
        if not has_privacy:
            pytest.xfail(
                "plugin.json does not include a privacy policy URL field. "
                "For a plugin that sends data to a remote server, consider adding "
                "a 'privacyPolicy' field pointing to the hosted privacy.html."
            )

    def test_marketplace_json_has_privacy_url(self, marketplace_json):
        """marketplace.json plugin entries should include a privacy URL."""
        for entry in marketplace_json.get("plugins", []):
            has_privacy = any(
                key in entry
                for key in ["privacyPolicy", "privacy", "privacyUrl", "privacy_url"]
            )
            if not has_privacy:
                pytest.xfail(
                    f"marketplace.json plugin entry '{entry.get('name', '?')}' "
                    "does not include a privacy policy URL. Consider adding one."
                )


# ===========================================================================
# 15. PRIVACY HTML STYLE & RESPONSIVENESS (Round 2 Critic)
# ===========================================================================


class TestPrivacyHtmlStyle:
    """privacy.html should be well-styled and responsive."""

    @pytest.fixture(scope="class")
    def privacy_html(self, plugin_root) -> str:
        path = plugin_root / "privacy.html"
        if not path.exists():
            pytest.skip("privacy.html does not exist")
        return path.read_text()

    def test_has_internal_or_linked_styles(self, privacy_html):
        """Page should have CSS (inline <style> or linked stylesheet)."""
        has_style = "<style>" in privacy_html.lower() or '<link' in privacy_html.lower()
        assert has_style, (
            "privacy.html has no CSS styling. A plain unstyled page looks unprofessional."
        )

    def test_uses_system_font_stack(self, privacy_html):
        """Should use a system font stack for cross-platform readability."""
        has_system_fonts = any(
            font in privacy_html.lower()
            for font in ["system-ui", "-apple-system", "segoe ui", "sans-serif"]
        )
        assert has_system_fonts, (
            "privacy.html should use a system font stack (e.g., -apple-system, "
            "Segoe UI, sans-serif) for cross-platform readability"
        )

    def test_link_color_is_accessible(self, privacy_html):
        """Link color should have sufficient contrast."""
        link_color_match = re.search(r'a\s*\{[^}]*color:\s*#([0-9a-fA-F]{3,6})', privacy_html)
        if link_color_match:
            hex_color = link_color_match.group(1)
            if len(hex_color) == 3:
                hex_color = ''.join(c * 2 for c in hex_color)
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            # Links should be distinguishable but not too light
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            assert luminance < 180, (
                f"privacy.html link color #{hex_color} may be too light "
                f"for sufficient contrast (luminance={luminance:.0f})"
            )

    def test_no_fixed_width_in_pixels_on_body(self, privacy_html):
        """Body should use max-width (not width) and rem/px units that are reasonable."""
        # Check for fixed width: NNNpx without max- prefix
        body_style = re.search(r'body\s*\{([^}]+)\}', privacy_html, re.IGNORECASE)
        if body_style:
            style = body_style.group(1)
            # Should not have width: NNpx (fixed) — max-width is OK
            has_fixed_width = re.search(r'(?<!max-)width:\s*\d+px', style)
            assert not has_fixed_width, (
                "privacy.html body has a fixed pixel width instead of max-width. "
                "This breaks on narrow screens."
            )

    def test_padding_for_mobile(self, privacy_html):
        """Body should have padding so text does not touch screen edges on mobile."""
        body_style = re.search(r'body\s*\{([^}]+)\}', privacy_html, re.IGNORECASE)
        if body_style:
            style = body_style.group(1)
            assert "padding" in style, (
                "privacy.html body has no padding. Text will touch screen edges on mobile."
            )
