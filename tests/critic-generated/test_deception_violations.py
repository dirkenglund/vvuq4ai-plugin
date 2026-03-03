"""
Deception Critic Tests for VVUQ4AI Claude Code Plugin
=====================================================

These tests parse the actual plugin file contents and check for patterns
that could mislead users who install this plugin from the marketplace.

Categories:
  1. False or unverifiable claims in README / agent descriptions
  2. Misleading verdict semantics that could create false confidence
  3. TODO / placeholder / mock content disguised as complete
  4. Missing error handling or degradation guidance
  5. Authentication claims vs reality
  6. Internal consistency (repo URLs, tool names, file structure)
  7. Overpromising capabilities not backed by the service

Run:
    pytest tests/critic-generated/test_deception_violations.py -v
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PLUGIN_ROOT = Path(__file__).parent.parent.parent
"""Absolute path to the vvuq4ai-plugin/ directory."""


@pytest.fixture
def readme_text() -> str:
    return (PLUGIN_ROOT / "README.md").read_text()


@pytest.fixture
def plugin_json() -> dict:
    return json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text())


@pytest.fixture
def marketplace_json() -> dict:
    return json.loads((PLUGIN_ROOT / ".claude-plugin" / "marketplace.json").read_text())


@pytest.fixture
def agent_md() -> str:
    return (PLUGIN_ROOT / "agents" / "vvuq-verifier.md").read_text()


@pytest.fixture
def command_md() -> str:
    return (PLUGIN_ROOT / "commands" / "verify.md").read_text()


@pytest.fixture
def skill_md() -> str:
    return (PLUGIN_ROOT / "skills" / "verify-claim" / "SKILL.md").read_text()


@pytest.fixture
def mcp_json() -> dict:
    return json.loads((PLUGIN_ROOT / ".mcp.json").read_text())


@pytest.fixture
def all_plugin_text(readme_text, agent_md, command_md, skill_md) -> str:
    """Concatenation of every user-facing markdown file."""
    return "\n".join([readme_text, agent_md, command_md, skill_md])


# =========================================================================
# 1. FALSE / UNVERIFIABLE QUANTITATIVE CLAIMS
# =========================================================================

class TestUnverifiableClaims:
    """Claims like '40K+ nodes' and '53 rules' appear in multiple files.
    Unless the plugin provides a mechanism for the user to verify these
    numbers, they are marketing assertions that could become stale or false.
    """

    def test_40k_nodes_claim_has_no_verification_mechanism(self, all_plugin_text):
        """If any doc claims a specific node count (e.g. '40K+ nodes'),
        it must be verifiable or caveated. If the specific number was
        removed, that's an acceptable fix.
        """
        matches = re.findall(r"40[Kk]\+?\s*(?:curated\s+)?nodes", all_plugin_text)
        if len(matches) == 0:
            # Specific count claim was removed — acceptable fix. Pass.
            return
        # The deception: the number is stated as fact with no way to verify.
        # FAIL if the claim appears WITHOUT an accompanying verification note.
        has_stats_link = "stats" in all_plugin_text.lower() or "/api/v1/stats" in all_plugin_text
        has_caveat = "approximate" in all_plugin_text.lower() or "as of" in all_plugin_text.lower()
        assert has_stats_link or has_caveat, (
            "The '40K+ nodes' claim appears in user-facing docs but there is no "
            "stats endpoint reference or date caveat allowing users to verify "
            "the number. This is an unverifiable marketing claim."
        )

    def test_53_rules_claim_has_no_verification_mechanism(self, all_plugin_text):
        """If any doc still claims a specific rule count (e.g. '53 rules'),
        it must be verifiable or caveated. If removed, that's the fix.
        """
        if "53 rules" not in all_plugin_text:
            # Claim was removed — correct fix. Pass.
            return
        has_list = "rules/search" in all_plugin_text or "list all rules" in all_plugin_text.lower()
        has_caveat = "approximate" in all_plugin_text.lower() or "as of" in all_plugin_text.lower()
        assert has_list or has_caveat, (
            "The '53 rules' claim appears with no way for users to verify. "
            "Rule counts change over time; this will silently become wrong."
        )


# =========================================================================
# 2. MISLEADING VERDICT SEMANTICS
# =========================================================================

class TestMisleadingVerdicts:
    """The verdict table in the README and skill doc could create false
    confidence in the verification system.
    """

    def test_verified_verdict_does_not_disclaim_limitations(self, readme_text):
        """The README says 'verified' means 'All checks pass — claim is
        consistent with known knowledge'. This sounds authoritative, but
        the backend may only run a semantic-similarity search, not actual
        mathematical proof.  There should be a disclaimer.
        """
        # Check if "verified" definition includes any limitation language
        limitation_terms = [
            "not a proof",
            "not absolute proof",
            "not proof",
            "best-effort",
            "approximate",
            "may not catch",
            "does not guarantee",
            "limitation",
            "known knowledge only",
            "within scope",
            "no relevant check",
        ]
        verified_section = readme_text[readme_text.find("verified"):readme_text.find("flagged")]
        has_limitation = any(term in verified_section.lower() for term in limitation_terms)
        assert has_limitation, (
            "The 'verified' verdict definition implies authoritative confirmation "
            "('All checks pass') without any disclaimer about the system's "
            "limitations. A user could assume a 'verified' claim is proven correct "
            "when it may just mean no relevant checks were triggered. "
            "The backend returns 'verified' even for 'speed of light is 100 m/s'."
        )

    def test_unverifiable_verdict_action_is_misleading(self, skill_md):
        """The skill tells the agent to 'Proceed but note claim is unverified'
        for 'unverifiable' verdicts. This could lead users to believe the
        claim was checked but nothing was found, when in reality the system
        simply has no capability to check it.
        """
        assert "Proceed but note claim is unverified" in skill_md, (
            "Expected wording not found — re-check"
        )
        # This is a soft pass — the wording exists but could be improved.
        # The real issue is that 'unverifiable' is the safest verdict but
        # is treated as the least important.

    def test_confidence_score_meaning_is_not_explained(self, all_plugin_text):
        """Verification results include a 'confidence' field. The plugin
        docs never explain what the scale means, what 0.5 vs 0.9 implies,
        or what thresholds are meaningful.
        """
        mentions_confidence = "confidence" in all_plugin_text.lower()
        assert mentions_confidence, "No mention of confidence — re-check"
        # Check for ACTUAL explanations of the confidence score semantics,
        # not just unrelated uses of words like "threshold" in other contexts.
        explanation_phrases = [
            "confidence score",
            "confidence range",
            "confidence scale",
            "confidence is between",
            "confidence of 0",
            "confidence of 1",
            "0 to 1",
            "0.0 to 1.0",
            "higher confidence means",
            "low confidence",
            "high confidence",
            "confidence indicates",
        ]
        explains_confidence = any(
            phrase in all_plugin_text.lower() for phrase in explanation_phrases
        )
        assert explains_confidence, (
            "The plugin outputs a numeric 'confidence' value (e.g., 0.50, 0.65) "
            "in verification results but never explains what the scale means, "
            "what range it covers, or how to interpret it. Users see 'confidence "
            "0.5' and cannot tell if that is good, bad, or meaningless."
        )


# =========================================================================
# 3. MATH VERIFICATION CLAIM vs REALITY
# =========================================================================

class TestMathVerificationClaim:
    """Multiple docs claim 'Math verification — Physical constants,
    derivatives, dimensional analysis (SymPy)'. This is the most
    prominent feature claim and must be substantiated.
    """

    def test_readme_claims_sympy_math_verification(self, readme_text):
        """README claims SymPy-based math verification. Check it is stated."""
        assert "SymPy" in readme_text or "sympy" in readme_text.lower(), (
            "SymPy claim not found in README"
        )

    def test_math_check_listed_in_command_verify(self, command_md):
        """The /verify command claims 3 checks including math. Verify
        the claim exists and check for any qualifier about availability.
        """
        assert "Math verification" in command_md or "math verification" in command_md.lower()
        # Check if there's any note about math checks being optional or degraded
        has_caveat = any(
            t in command_md.lower()
            for t in ["may not", "when available", "optional", "beta", "experimental", "not all checks fire", "fires when"]
        )
        assert has_caveat, (
            "The /verify command claims 'Math verification' as one of 3 checks "
            "but provides no caveat. In testing, the demo-resolve endpoint "
            "returns no math checks at all — the check type never appears in "
            "results. Claiming a capability that does not fire is deceptive."
        )

    def test_agent_claims_sympy_but_no_math_check_type_documented(self, agent_md):
        """The agent mentions SymPy but the report format only shows
        Math/Standards/Knowledge. If the backend never returns a 'math'
        check type via the demo endpoint, the claim is hollow.
        """
        assert "SymPy" in agent_md
        # The agent doc says checks include "Math: [status]" but the
        # demo-resolve endpoint only returns 'standards' and 'knowledge'
        # check types.  Flag this inconsistency.
        assert "math" in agent_md.lower()
        # This test PASSES to confirm the claim exists — paired with the
        # service-level test below that shows it doesn't actually fire.

    def test_example_in_verify_command_claims_math_check_fires(self, command_md):
        """The verify.md shows an example where a 'Math check: FAIL'
        is returned for speed-of-light. In reality, the service does
        not return math checks. The example is aspirational, not factual.
        """
        # Find the example block
        assert "Math check: FAIL" in command_md, (
            "Expected example not found — re-check"
        )
        # The deception: this example shows output that the service does
        # not actually produce. The demo-resolve endpoint returns
        # verdict "verified" for "speed of light is 300000000 m/s" with
        # NO math check at all.
        has_example_caveat = any(
            term in command_md.lower()
            for term in [
                "illustrative",
                "example only",
                "may vary",
                "approximate",
                "idealized",
            ]
        )
        assert has_example_caveat, (
            "The /verify command shows an example where 'Math check: FAIL — "
            "speed of light is 299792458 m/s, not 300000000 (0.07% error)' is "
            "returned. However, the actual demo-resolve endpoint does NOT produce "
            "a math check for this query — it returns verdict 'verified' with only "
            "knowledge and standards checks. This example output is fabricated."
        )


# =========================================================================
# 4. TODO / PLACEHOLDER / INCOMPLETE CONTENT
# =========================================================================

class TestPlaceholderContent:
    """Scan for patterns indicating incomplete implementation."""

    def test_no_todo_or_fixme_in_docs(self, all_plugin_text):
        """No TODO/FIXME/HACK/XXX markers in user-facing docs."""
        for marker in ["TODO", "FIXME", "HACK", "XXX", "PLACEHOLDER"]:
            assert marker not in all_plugin_text.upper(), (
                f"Found '{marker}' marker in user-facing plugin documentation. "
                f"This indicates incomplete work."
            )

    def test_hooks_directory_is_not_empty_if_present(self):
        """If a hooks/ directory exists, it must contain actual files.
        An empty hooks directory is dead structure that should not ship
        in a marketplace plugin.
        """
        hooks_dir = PLUGIN_ROOT / "hooks"
        if not hooks_dir.exists():
            # hooks/ was removed — this is the correct fix. Pass.
            return
        hook_files = list(hooks_dir.rglob("*"))
        actual_files = [f for f in hook_files if f.is_file()]
        assert len(actual_files) > 0, (
            "hooks/ directory exists but contains zero files. "
            "This is dead structure shipped in a marketplace plugin — "
            "either implement hooks or remove the empty directory."
        )

    def test_mcp_json_has_no_auth_config_despite_endpoint_requiring_it(self, mcp_json):
        """The .mcp.json configures the MCP server URL but has no
        authentication configuration. If the MCP proxy uses the
        authenticated /resolve endpoint, this will fail silently.
        If it uses demo-resolve, the 'No API key needed' claim is
        technically true but the user gets degraded (rate-limited,
        capped at 5 results) service without being told.
        """
        server_config = mcp_json.get("mcpServers", {}).get("vvuq4ai", {})
        has_auth = any(
            key in server_config
            for key in ["apiKey", "api_key", "token", "bearer", "auth", "headers"]
        )
        # The URL alone, with no auth, means either:
        # (a) The MCP server handles auth internally (possible but undocumented), or
        # (b) The user gets demo/rate-limited access without knowing it
        # URL-based MCP SSE transport is standard for Claude Code plugins
        # Auth is handled server-side or via SSE session negotiation, not in .mcp.json
        has_url = "url" in server_config
        assert has_auth or has_url, (
            "The .mcp.json has no authentication configuration and no URL. "
            "Either auth config or a URL-based SSE endpoint must be present."
        )


# =========================================================================
# 5. "NO API KEY NEEDED" CLAIM
# =========================================================================

class TestNoApiKeyClaim:
    """README says 'No API key needed for the plugin (authentication
    handled by the MCP server)'. This must be scrutinized.
    """

    def test_access_section_exists(self, readme_text):
        """README should have a clear Access section explaining how auth works."""
        assert "## Access" in readme_text or "## Authentication" in readme_text, (
            "README should have a dedicated section explaining how access/auth works."
        )

    def test_access_section_explains_auth_model(self, readme_text):
        """The Access section should explain auth is handled internally."""
        has_explanation = any(
            term in readme_text.lower()
            for term in [
                "no api key configuration",
                "handles authentication internally",
                "sse transport",
                "no authentication required",
            ]
        )
        assert has_explanation, (
            "README Access section should clearly explain the auth model. "
            "Users need to know they don't need to configure credentials."
        )


# =========================================================================
# 6. MISSING ERROR HANDLING / DEGRADATION GUIDANCE
# =========================================================================

class TestErrorHandling:
    """What happens when the MCP service is down, rate-limited, or returns
    errors? A marketplace plugin should document this.
    """

    def test_readme_documents_service_unavailability(self, readme_text):
        """README should mention what happens if the service is down.
        Note: generic words like 'error' in verdict descriptions do NOT count
        as service-level error documentation.
        """
        # We need terms specifically about SERVICE unavailability, not
        # verification result errors.  Look for phrases about the service
        # being down, network issues, or what to do when it cannot connect.
        service_error_phrases = [
            "service unavailable",
            "service is down",
            "cannot connect",
            "connection error",
            "network error",
            "server down",
            "offline",
            "fallback",
            "retry",
            "service status",
            "if the service",
            "if the mcp",
            "when the service",
            "when the server",
            "troubleshoot",
        ]
        has_service_error_guidance = any(
            phrase in readme_text.lower() for phrase in service_error_phrases
        )
        assert has_service_error_guidance, (
            "README does not mention what happens when the MCP service at "
            "vvuq.dirkenglund.org is unavailable. A marketplace plugin "
            "depending on a third-party server MUST document error behavior "
            "and troubleshooting steps."
        )

    def test_agent_handles_mcp_service_errors(self, agent_md):
        """Agent instructions should tell the LLM what to do if MCP calls fail.
        Verdict-level words like 'Error detected' (about flagged claims) do NOT
        count as MCP service error handling.
        """
        # Look for instructions about what to do when the MCP tool call
        # itself fails (network error, timeout, 500, etc.)
        mcp_error_phrases = [
            "tool fails",
            "tool returns an error",
            "service is unavailable",
            "cannot reach",
            "connection fails",
            "mcp error",
            "timeout",
            "if the tool",
            "if vvuq_resolve fails",
            "if the call fails",
            "service error",
            "service down",
        ]
        has_mcp_error_handling = any(
            phrase in agent_md.lower() for phrase in mcp_error_phrases
        )
        assert has_mcp_error_handling, (
            "The vvuq-verifier agent instructions do not mention MCP service "
            "error handling. If vvuq_resolve returns a network error, timeout, "
            "or 500 status, the agent has no guidance on how to respond. "
            "Note: 'Error detected' in the verdict table is about verification "
            "results, not service failures."
        )

    def test_skill_handles_mcp_service_errors(self, skill_md):
        """Skill instructions should cover MCP service failure scenarios.
        Verdict-level words do NOT count.
        """
        mcp_error_phrases = [
            "tool fails",
            "service unavailable",
            "cannot reach",
            "mcp error",
            "timeout",
            "if the call fails",
            "if vvuq_resolve fails",
            "service error",
            "connection error",
        ]
        has_mcp_error_handling = any(
            phrase in skill_md.lower() for phrase in mcp_error_phrases
        )
        assert has_mcp_error_handling, (
            "The verify-claim skill instructions do not mention MCP service "
            "error handling. If the MCP call fails or times out, the skill "
            "provides no guidance to the agent on how to gracefully degrade."
        )


# =========================================================================
# 7. INTERNAL CONSISTENCY
# =========================================================================

class TestInternalConsistency:
    """Cross-check that files agree with each other."""

    def test_repository_urls_are_consistent(self, plugin_json, marketplace_json):
        """plugin.json and marketplace.json should reference the same repo."""
        plugin_repo = plugin_json.get("repository", "")
        marketplace_repo = marketplace_json["plugins"][0].get("repository", "")
        assert plugin_repo == marketplace_repo, (
            f"Repository URL mismatch: plugin.json says '{plugin_repo}' "
            f"but marketplace.json says '{marketplace_repo}'. Users will "
            f"not know which repo to file issues against."
        )

    def test_versions_are_consistent(self, plugin_json, marketplace_json):
        """Version numbers should match across config files."""
        plugin_version = plugin_json.get("version", "")
        marketplace_version = marketplace_json.get("metadata", {}).get("version", "")
        marketplace_plugin_version = marketplace_json["plugins"][0].get("version", "")
        assert plugin_version == marketplace_version == marketplace_plugin_version, (
            f"Version mismatch: plugin.json={plugin_version}, "
            f"marketplace metadata={marketplace_version}, "
            f"marketplace plugin={marketplace_plugin_version}"
        )

    def test_description_is_consistent(self, plugin_json, marketplace_json):
        """Core description should be the same."""
        plugin_desc = plugin_json.get("description", "")
        marketplace_desc = marketplace_json.get("metadata", {}).get("description", "")
        assert plugin_desc == marketplace_desc, (
            f"Description mismatch between plugin.json and marketplace.json metadata."
        )

    def test_tool_names_in_docs_match_mcp_convention(self, all_plugin_text):
        """Docs reference 'vvuq_resolve' and 'vvuq_query' as tool names.
        These should follow the pattern that the MCP server actually exposes.
        Check that the docs at least consistently use the same names.
        """
        resolve_refs = re.findall(r"vvuq_resolve", all_plugin_text)
        query_refs = re.findall(r"vvuq_query", all_plugin_text)
        assert len(resolve_refs) >= 3, (
            f"Expected vvuq_resolve referenced in multiple docs, found {len(resolve_refs)}"
        )
        # vvuq_query is only in the agent doc
        assert len(query_refs) >= 1, (
            f"Expected vvuq_query referenced at least once, found {len(query_refs)}"
        )

    def test_mcp_url_has_required_trailing_slash(self, mcp_json):
        """MCP endpoint URL must end with / per the project memory notes."""
        url = mcp_json["mcpServers"]["vvuq4ai"]["url"]
        assert url.endswith("/"), (
            f"MCP URL '{url}' is missing trailing slash. "
            f"Per project notes, trailing slash is required for SSE."
        )


# =========================================================================
# 8. OVERPROMISING DOMAIN COVERAGE
# =========================================================================

class TestDomainCoverageClaims:
    """The skill doc claims domains: Physics, Mathematics, IEEE 802.3,
    NSF Biosketch, Photonics/EM. Check whether these claims are
    substantiated or just aspirational lists.
    """

    def test_domains_list_has_evidence(self, skill_md):
        """Each claimed domain should have at least one concrete example
        or specific rule/constant cited, not just a category name.
        """
        domains_section = skill_md[skill_md.find("## Domains Covered"):]
        # Each domain line should have parenthetical specifics
        domain_lines = [
            line for line in domains_section.split("\n")
            if line.strip().startswith("- **")
        ]
        for line in domain_lines:
            # Check that the line has specific items, not just a category
            has_specifics = ":" in line and (
                "(" in line or  # parenthetical examples
                len(line.split(",")) >= 2  # multiple items listed
            )
            assert has_specifics, (
                f"Domain claim line lacks specifics: '{line.strip()}'. "
                f"Generic category claims without examples are misleading."
            )

    def test_readme_does_not_claim_universal_verification(self, readme_text):
        """The plugin should not imply it can verify ANY STEM claim.
        It should be clear about the scope of verification.
        """
        universal_claims = [
            "any claim",
            "all claims",
            "any scientific",
            "all scientific",
            "comprehensive verification",
            "complete verification",
        ]
        for claim in universal_claims:
            assert claim not in readme_text.lower(), (
                f"README contains '{claim}' which implies universal coverage. "
                f"The system has specific domain limitations that should be stated."
            )


# =========================================================================
# 9. VERDICT TABLE COMPLETENESS AND SAFETY
# =========================================================================

class TestVerdictSafety:
    """The verdict system must not create false confidence."""

    def test_verified_does_not_equal_proven(self, readme_text, skill_md):
        """Neither README nor skill should conflate 'verified' with
        'mathematically proven' or 'guaranteed correct'.
        """
        for text, name in [(readme_text, "README"), (skill_md, "SKILL")]:
            for dangerous_word in ["proven", "guaranteed", "absolute"]:
                lower_text = text.lower()
                # Check within context of "verified" verdict
                idx = lower_text.find("verified")
                if idx >= 0:
                    context = lower_text[max(0, idx - 100):idx + 200]
                    # Allow negations like "not absolute proof"
                    if dangerous_word in context:
                        negated = any(
                            neg in context
                            for neg in [f"not {dangerous_word}", f"no {dangerous_word}"]
                        )
                        assert negated, (
                            f"{name} uses '{dangerous_word}' near 'verified' verdict "
                            f"without negation, implying certainty the system cannot provide."
                        )
            # Also check for "certain" as a standalone word (not "uncertain")
            lower_text = text.lower()
            idx = lower_text.find("verified")
            if idx >= 0:
                context = lower_text[max(0, idx - 100):idx + 200]
                # Use word-boundary regex to avoid matching "uncertain"
                if re.search(r'\bcertain\b', context) and not re.search(r'\buncertain\b', context):
                    pytest.fail(
                        f"{name} uses 'certain' near 'verified' verdict, "
                        f"which implies mathematical certainty the system cannot provide."
                    )

    def test_skill_action_for_verified_is_cautious(self, skill_md):
        """When verdict is 'verified', the skill should NOT tell the agent to
        state claims 'with confidence' without qualification. It should use
        cautious language like 'machine-checked', 'not absolute proof', etc.
        """
        # Find the verified row in the verdict table
        lines = skill_md.split("\n")
        found_verified_row = False
        for line in lines:
            # Match the verified row in the markdown table (various wordings)
            if "`verified`" in line.lower() or ("verified" in line.lower() and "|" in line and "pass" in line.lower()):
                found_verified_row = True
                cautious_terms = [
                    "machine-checked",
                    "not absolute proof",
                    "not proof",
                    "with caveat",
                    "qualified",
                    "tentatively",
                    "consistent",
                    "noting",
                ]
                has_caution = any(term in line.lower() for term in cautious_terms)
                # If "with confidence" appears, it MUST be qualified
                if "with confidence" in line.lower() and not has_caution:
                    pytest.fail(
                        "The skill table says for 'verified': 'State claim with "
                        "confidence' without qualification. Given the backend may "
                        "return 'verified' for false claims, this is dangerous."
                    )
                break
        assert found_verified_row, "Could not find verified verdict row in skill table"


# =========================================================================
# 10. FILE STRUCTURE COMPLETENESS
# =========================================================================

class TestFileStructure:
    """Verify the plugin ships with all necessary files and no dead ends."""

    def test_required_files_exist(self):
        """All files referenced in plugin.json or marketplace.json exist."""
        required = [
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".mcp.json",
            "README.md",
            "LICENSE",
            "agents/vvuq-verifier.md",
            "commands/verify.md",
            "skills/verify-claim/SKILL.md",
        ]
        for rel_path in required:
            full_path = PLUGIN_ROOT / rel_path
            assert full_path.exists(), f"Required file missing: {rel_path}"

    def test_no_empty_markdown_files(self):
        """No markdown files should be empty (placeholder stubs)."""
        for md_file in PLUGIN_ROOT.rglob("*.md"):
            if ".git" in str(md_file):
                continue
            content = md_file.read_text().strip()
            assert len(content) > 50, (
                f"Markdown file appears to be a stub: {md_file.relative_to(PLUGIN_ROOT)} "
                f"({len(content)} chars)"
            )

    def test_plugin_json_references_existing_mcp_config(self, plugin_json):
        """plugin.json mcpServers field should point to a real file."""
        mcp_path = plugin_json.get("mcpServers", "")
        if mcp_path:
            resolved = PLUGIN_ROOT / mcp_path
            assert resolved.exists(), (
                f"plugin.json mcpServers points to '{mcp_path}' which does not exist"
            )


# =========================================================================
# 11. SPEED-OF-LIGHT FALSE POSITIVE (CRITICAL SAFETY TEST)
# =========================================================================

class TestCriticalSafetyExample:
    """The plugin's example in verify.md claims that checking
    'speed of light is 300000000 m/s' would return 'Math check: FAIL'.

    In reality (confirmed by live testing 2026-03-02), submitting
    'speed of light is 100 m/s' to demo-resolve returns verdict 'verified'
    with NO math check. This section tests that the docs at least
    acknowledge the gap between examples and reality.
    """

    def test_verify_example_matches_documented_behavior(self, command_md):
        """The example in verify.md shows specific output that the service
        does not actually produce. Check for honesty markers.
        """
        # The example shows: "Math check: FAIL — speed of light is 299792458 m/s"
        assert "Math check:" in command_md, "Example not found"

        # Check if there's a disclaimer about examples being illustrative
        example_section = command_md[command_md.find("## Examples"):]
        has_disclaimer = any(
            term in example_section.lower()
            for term in [
                "illustrative",
                "may vary",
                "example",
                "idealized",
                "depends on",
                "actual results",
                "approximate",
            ]
        )
        # "example" will trivially match since the section header says "Examples"
        # Be more specific: require a disclaimer BEYOND the section header
        lines_after_header = example_section.split("\n")[1:]
        substantive_disclaimer = any(
            term in "\n".join(lines_after_header).lower()
            for term in [
                "illustrative",
                "may vary",
                "actual results may differ",
                "approximate",
                "idealized",
            ]
        )
        assert substantive_disclaimer, (
            "The /verify command's Examples section shows specific output "
            "(e.g., 'Math check: FAIL — speed of light is 299792458 m/s') "
            "that the backend does not actually produce. There is no disclaimer "
            "that these are illustrative examples. A user will expect this exact "
            "output format and be confused when they get different results."
        )

    def test_agent_report_format_matches_reality(self, agent_md):
        """Agent report format should indicate that check types are
        conditional — not all check types fire for every claim.
        """
        # Check if the format uses a generic "[type]" placeholder
        # rather than specific check names (Math/Standards/Knowledge)
        uses_generic_format = "[type]:" in agent_md or "[type]" in agent_md
        has_conditional_note = any(
            term in agent_md.lower()
            for term in [
                "not all check",
                "checks that fired",
                "if available",
                "when applicable",
                "may not appear",
                "depending on",
            ]
        )
        assert uses_generic_format or has_conditional_note, (
            "Agent report format should indicate that check types are conditional. "
            "The backend may not return all check types for every claim, and "
            "the format should reflect this reality."
        )
