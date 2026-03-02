# VVUQ4AI — Claude Code Plugin

Verify AI-generated STEM claims against curated knowledge bases, IEEE standards, and mathematical proofs.

## What It Does

VVUQ4AI checks scientific, engineering, and mathematical claims for accuracy using:

- **Math verification** — Physical constants, derivatives, dimensional analysis (SymPy)
- **Standards compliance** — IEEE 802.3 Ethernet channel rules, NSF Biosketch format
- **Knowledge cross-reference** — 40K+ curated nodes from physics, math, CS, photonics

## Installation

```bash
claude plugin add /path/to/vvuq4ai-plugin
```

Or add to your project's `.claude/plugins/`:

```bash
cp -r vvuq4ai-plugin ~/.claude/plugins/vvuq4ai
```

## Usage

### Command: `/verify`

```
/verify The speed of light is 300000000 m/s
```

Returns a structured verification with verdict, confidence, and individual check results.

### Agent: vvuq-verifier

Automatically triggered when reviewing technical documents or when STEM claims need verification. Use the Task tool with `subagent_type: "vvuq-verifier"`.

### Skill: verify-claim

Auto-activates when Claude generates numeric scientific claims, unit conversions, standards references, or mathematical formulas.

## Verdicts

| Verdict | Meaning |
|---------|---------|
| `verified` | All checks pass — claim is consistent with known knowledge |
| `flagged` | Error detected — at least one check found an issue |
| `uncertain` | Mixed results — some checks passed, others inconclusive |
| `unverifiable` | No applicable checks for this claim |

## Requirements

- Claude Code CLI
- Internet access (connects to https://vvuq.dirkenglund.org/mcp/)
- No API key needed for the plugin (authentication handled by the MCP server)

## License

MIT
