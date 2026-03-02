---
name: verify-claim
description: Use when Claude generates or encounters STEM claims that could benefit from verification — physics constants, mathematical identities, engineering standards compliance, or factual assertions about science and engineering. Automatically triggered when output contains numeric scientific claims, unit conversions, standards references, or mathematical formulas.
version: 0.1.0
---

# VVUQ4AI Claim Verification Skill

## When This Activates

This skill should be used when you:
- Generate a claim about a physical constant (speed of light, Planck's constant, etc.)
- State a mathematical identity or derivative
- Reference IEEE, NSF, or other standards compliance
- Make dimensional analysis assertions (units, conversions)
- Produce engineering specifications with numeric thresholds

## How To Verify

Call the `vvuq_resolve` MCP tool with the claim text:

```
vvuq_resolve(query="<claim to verify>")
```

The response includes:
- `results`: Related knowledge base entries (for context)
- `verification`: Structured verdict with checks

## Verification Verdicts

| Verdict | Meaning | Action |
|---------|---------|--------|
| `verified` | All checks pass | State claim with confidence |
| `flagged` | Error detected | Correct the claim, cite the check detail |
| `uncertain` | Mixed signals | Qualify the claim, note uncertainty |
| `unverifiable` | No applicable checks | Proceed but note claim is unverified |

## Integration Pattern

When generating STEM content:

1. Write your response normally
2. For key claims, call `vvuq_resolve` to verify
3. If flagged: correct the error inline, cite the verification
4. If uncertain: add a caveat noting the uncertainty
5. If verified: optionally note it was machine-verified

## Example Flow

You're writing about fiber optic standards:

> "A channel with COM of 2.5 dB meets IEEE 802.3ck compliance."

Before stating this, verify:
```
vvuq_resolve(query="COM of 2.5 dB meets IEEE 802.3ck compliance")
```

Response: `verdict: "flagged"` — COM must be >= 3.0 dB per IEEE8023:com-minimum

Corrected output:
> "A channel with COM of 2.5 dB does **not** meet IEEE 802.3ck compliance, which requires COM >= 3.0 dB (per IEEE Std 802.3ck-2022, Annex 93A)."

## Domains Covered

- **Physics**: Constants (c, h, k_B, G, e, m_e), equations, dimensional analysis
- **Mathematics**: Identities, derivatives, integrals
- **IEEE 802.3**: Ethernet channel compliance (COM, insertion loss, TDECQ, return loss, etc.)
- **NSF Biosketch**: Grant format compliance
- **Photonics/EM**: Device parameters, simulation validation
