---
name: verify
description: Verify an AI-generated STEM claim against the VVUQ4AI knowledge base, IEEE standards, and mathematical checks
argument-hint: "<STEM claim to verify>"
---

# /verify — VVUQ4AI Claim Verification

Verify a scientific, engineering, or mathematical claim using the VVUQ4AI service.

## What This Does

Takes a STEM claim and runs it through 3 verification checks:
1. **Math verification** — Physical constants, derivatives, dimensional analysis, identities (SymPy)
2. **Standards checking** — IEEE 802.3, NSF Biosketch, and other normative rule compliance
3. **Knowledge cross-reference** — Semantic search against 40K+ curated knowledge nodes

## How To Use

When the user provides a claim to verify, call the `vvuq_resolve` MCP tool:

```
vvuq_resolve(query="<the claim>")
```

## Interpreting Results

The response includes a `verification` object:

- **verdict: "verified"** — All checks pass. The claim is consistent with known knowledge.
- **verdict: "flagged"** — At least one check found an error. Report which check(s) failed and why.
- **verdict: "uncertain"** — Mixed results. Some checks passed, others couldn't determine. Report what's known and what's uncertain.
- **verdict: "unverifiable"** — The claim doesn't contain verifiable content (no math, no standards, no KB matches).

Always report:
1. The overall verdict and confidence
2. Each individual check's result (type, status, detail)
3. The top search results for additional context

## Examples

User: `/verify The speed of light is 300000000 m/s`

Response should include:
- Math check: FAIL — speed of light is 299792458 m/s, not 300000000 (0.07% error)
- Overall verdict: flagged (confidence 0.9)

User: `/verify COM of 4.5 dB meets IEEE 802.3ck compliance`

Response should include:
- Standards check: PASS — COM 4.5 dB >= 3.0 dB minimum per IEEE8023:com-minimum
- Overall verdict: verified or uncertain (depends on KB match)
