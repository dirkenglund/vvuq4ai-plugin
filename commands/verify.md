---
name: verify
description: Verify an AI-generated STEM claim against the VVUQ4AI knowledge base, IEEE standards, and mathematical checks
argument-hint: "<STEM claim to verify>"
---

# /verify — VVUQ4AI Claim Verification

Verify a scientific, engineering, or mathematical claim using the VVUQ4AI service.

## What This Does

Takes a STEM claim and runs it through up to 3 verification checks (not all checks fire for every claim):
1. **Math verification** — Physical constants, derivatives, dimensional analysis, identities (SymPy). Fires when the claim contains recognizable numeric values or formulas.
2. **Standards checking** — IEEE 802.3, NSF Biosketch, and other normative rule compliance. Fires when claim references a standard or parameter name.
3. **Knowledge cross-reference** — Semantic search against curated knowledge nodes from physics, math, CS, and photonics.

## How To Use

When the user provides a claim to verify, call the `vvuq_resolve` MCP tool:

```
vvuq_resolve(query="<the claim>")
```

If the MCP call fails (network error, timeout, service unavailable), inform the user that the verification service is temporarily unavailable and the claim could not be checked.

## Interpreting Results

The response includes a `verification` object:

- **verdict: "verified"** — Checks that fired all passed. Note: this means consistency with known knowledge, not absolute proof of correctness. Some claims may pass simply because no relevant check was triggered.
- **verdict: "flagged"** — At least one check found an error. Report which check(s) failed and why.
- **verdict: "uncertain"** — Mixed results. Some checks passed, others couldn't determine. Report what's known and what's uncertain.
- **verdict: "unverifiable"** — The claim doesn't contain verifiable content (no math, no standards, no KB matches).

The confidence score (0.0–1.0) reflects how strongly the checks support the verdict. Higher values mean more checks fired and agreed. A low confidence verified result means few checks were applicable.

Always report:
1. The overall verdict and confidence score
2. Each individual check's result (type, status, detail) — only checks that fired will appear
3. The top search results for additional context

## Examples

These are illustrative — actual output format may vary depending on which checks fire.

User: `/verify The speed of light is 300000000 m/s`

Typical response:
- Math check: FAIL — speed of light is 299792458 m/s, not 300000000 (0.07% error)
- Overall verdict: flagged (confidence 0.9)

User: `/verify COM of 4.5 dB meets IEEE 802.3ck compliance`

Typical response:
- Standards check: PASS — COM 4.5 dB >= 3.0 dB minimum per IEEE8023:com-minimum
- Overall verdict: verified or uncertain (depends on KB match)
