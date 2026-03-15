# VVUQ4AI — Claude Code Plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Verify AI-generated STEM claims against curated knowledge bases, IEEE standards, and mathematical checks.

## Installation

```shell
/plugin marketplace add dirkenglund/vvuq4ai-plugin
/plugin install vvuq4ai@vvuq4ai
```

## What it does

When installed, Claude gains access to VVUQ verification tools via MCP. These tools let Claude check physics constants, mathematical identities, IEEE 802.3 compliance, and more against a curated knowledge base of 40K+ nodes.

## Example

```
You: "Is the speed of light 300,000,000 m/s?"
Claude (with VVUQ): "Flagged — the accepted value is 299,792,458 m/s (0.07% error)."
```

## Requirements

- Claude Code CLI
- Internet access (connects to `https://vvuq.dirkenglund.org/mcp/`)
- No API key needed

## Privacy

Claim text is sent to the VVUQ service for verification. See the [privacy policy](https://vvuq.dirkenglund.org/privacy).

## License

MIT
