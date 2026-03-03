# VVUQ4AI — Claude Code Plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/dirkenglund/vvuq4ai-plugin/actions/workflows/tests.yml/badge.svg)](https://github.com/dirkenglund/vvuq4ai-plugin/actions/workflows/tests.yml)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](.claude-plugin/plugin.json)

Verify AI-generated STEM claims against curated knowledge bases, IEEE standards, and mathematical checks.

## How It Works

1. You type `/verify <claim>` (or the skill auto-triggers on STEM content)
2. Claude calls `vvuq_resolve()` on the VVUQ MCP service via SSE
3. The service runs up to 3 checks: math (SymPy), standards (IEEE/NSF), and knowledge base semantic search
4. Returns a verdict, confidence score, and individual check results

Not all checks fire for every claim — the system applies whichever checks are relevant to the input.

## What Can It Verify?

| Domain | Examples |
|--------|----------|
| **Physics constants** | Speed of light, Planck's constant, Boltzmann constant, gravitational constant, electron mass |
| **Mathematical identities** | Derivatives, integrals, trigonometric identities, dimensional analysis |
| **IEEE 802.3 Ethernet** | COM threshold (>= 3.0 dB), insertion loss, TDECQ, return loss per IEEE 802.3ck |
| **NSF Biosketch** | Section requirements, page limits, format compliance |
| **Photonics/EM** | Device parameters, simulation validation, waveguide properties |

## Installation

### From marketplace (recommended)

```shell
/plugin marketplace add dirkenglund/vvuq4ai-plugin
/plugin install vvuq4ai@vvuq4ai
```

### Local development

```bash
claude --plugin-dir ./vvuq4ai-plugin
```

## Usage

### Command: `/verify`

```shell
/verify The speed of light is 300000000 m/s
```

VVUQ4AI will flag this: the correct value is 299792458 m/s (0.07% error). Returns a structured verification with verdict, confidence, and individual check results.

### Agent: vvuq-verifier

Automatically triggered when reviewing technical documents or when STEM claims need verification. Use the Task tool with `subagent_type: "vvuq-verifier"`.

### Skill: verify-claim

Auto-activates when Claude generates numeric scientific claims, unit conversions, standards references, or mathematical formulas.

## Verdicts

| Verdict | Meaning |
|---------|---------|
| `verified` | Checks that fired all passed — consistent with known knowledge (not absolute proof) |
| `flagged` | Error detected — at least one check found an issue |
| `uncertain` | Mixed results — some checks passed, others inconclusive |
| `unverifiable` | No applicable checks for this claim |

## Requirements

- Claude Code CLI
- Internet access (connects to `https://vvuq.dirkenglund.org/mcp/`)
- No API key or configuration needed

## Access

The plugin connects to the VVUQ MCP service via SSE transport. No API key configuration is needed in the plugin — the MCP endpoint handles authentication internally. If the service is unavailable, verification calls will fail gracefully and the plugin will report that the claim could not be verified.

## Troubleshooting

- **Service unavailable**: The VVUQ service runs on a remote server. If you get connection errors, the service may be temporarily down. Try again later.
- **No checks fired**: Some claims don't match any verification rules. The verdict will be "unverifiable" — this doesn't mean the claim is wrong, just that no automated check could be applied.

## Privacy

This plugin sends claim text to the VVUQ verification service at `https://vvuq.dirkenglund.org/mcp/`. See the [privacy policy](https://vvuq.dirkenglund.org/privacy) for details on data collection, retention, and opt-out options.

## License

MIT
