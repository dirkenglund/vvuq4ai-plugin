---
name: formalize
description: "Interactive formalization with VVUQ contract verification — extract claims, create contracts, submit proofs, iterate until ACCEPTED"
argument-hint: "<paper/goal description> [domain]"
allowed-tools: ["Task", "Read", "Write", "Edit", "MultiEdit", "Grep", "Glob", "TodoWrite", "Bash", "WebFetch", "AskUserQuestion"]
---

# /formalize — Contract-Verified Formalization

Generate a formal specification from a paper or design goal. Key claims become **VVUQ contracts** with Lean4 theorem statements. Proofs are submitted and must be **ACCEPTED** by the VVUQ verification engine before the spec is finalized.

## Usage

```bash
/vvuq4ai:formalize "quadratic formula correctness"
/vvuq4ai:formalize "Fabry-Perot cavity with finesse >100" photonic
/vvuq4ai:formalize "energy conservation in ring resonator" photonic
```

## Domains

- `general` (default) — any STEM specification
- `photonic` — waveguides, resonators, interferometers
- `circuit` — electronic circuits, impedance, SPICE
- `optimization` — constrained optimization, cost functions
- `mathematics` — formal proofs, identities

## Execute

**Description**: $ARGUMENTS

Starting contract-verified formalization...

### Phase 1: Source Ingestion

1. Parse source (PDF, paper, user description)
2. Extract equations, assumptions, key claims
3. Identify domain
4. Search VVUQ knowledge base:
   ```
   vvuq_resolve(query="<key claim>")
   ```

### Phase 2: MathObject Identification (dual sign-off)

For each equation, propose a MathObject with:
- Name, symbol, LaTeX, Python expression, units, bounds
- **Lean4 theorem statement** — the formal claim to verify

Present ONE at a time. Both user AND critic must approve.

### Phase 3: Create VVUQ Contract

For each approved MathObject that has a Lean4 theorem, create a contract:

```bash
# Create contract via VVUQ API
VVUQ_API_KEY="$(gcloud secrets versions access latest --secret=VVUQ_API_KEY)"
curl -s -X POST https://vvuq.dirkenglund.org/api/v1/contracts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $VVUQ_API_KEY" \
  -d '{
    "title": "<MathObject name>",
    "description": "<what this proves>",
    "claims": [{
      "theorem": "<Lean4 theorem statement>",
      "allowed_imports": ["Mathlib.Tactic", ...],
      "mathlib_version": "v4.15.0"
    }],
    "issuer_agent_id": "vvuq4ai-formalize"
  }'
```

Record the `contract_id` for each MathObject.

### Phase 4: Submit Proofs (iterate until ACCEPTED)

For each contract, generate a Lean4 proof and submit:

```bash
curl -s -X POST https://vvuq.dirkenglund.org/api/v1/proofs/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $VVUQ_API_KEY" \
  -d '{
    "contract_id": "<contract_id>",
    "claim_id": 1,
    "prover_agent_id": "vvuq4ai-formalize",
    "proof_code": "<Lean4 proof>"
  }'
```

Poll for result:
```bash
curl -s https://vvuq.dirkenglund.org/api/v1/verifications/<verification_id>/status \
  -H "X-API-Key: $VVUQ_API_KEY"
```

**If REJECTED**: Read the error, fix the proof, resubmit. Up to 5 attempts per claim.

**If ACCEPTED**: Record verification_id. This MathObject is formally verified.

**If ERROR**: Log and flag for manual review.

### Phase 5: Constraint Classification (dual sign-off)

Classify constraints:
- **Hard constraints**: Physical laws (VVUQ-verified via contracts)
- **Soft constraints**: Design targets
- **Parameter bounds**: Valid ranges

### Phase 6: Test Predicate Generation (dual sign-off)

Generate pytest tests. For VVUQ-verified claims, reference the contract:

```python
def test_quadratic_formula():
    """VVUQ Contract: contract_2a8d51b1b8b3 — ACCEPTED
    Theorem: ∀ a b c, a≠0 → b²-4ac≥0 → a·x²+b·x+c = 0
    """
    a, b, c = 1.0, -3.0, 2.0
    x = (-b + math.sqrt(b**2 - 4*a*c)) / (2*a)
    assert abs(a*x**2 + b*x + c) < 1e-10
```

### Phase 7: Cost Function (dual sign-off)

Weight verified claims higher:
```python
cost_function = {
    "vvuq_verified": {"weight": 3.0, "tests": [...]},    # Contract ACCEPTED
    "hard_constraints": {"weight": 1.0, "tests": [...]},  # Physics laws
    "design_targets": {"weight": 0.5, "tests": [...]},    # Soft goals
}
```

### Phase 8: Final Spec (dual sign-off)

Output:
1. **SPEC.md** — with contract IDs, verification IDs, and sign-off log
2. **tests/test_spec.py** — failing tests (RED state)
3. Cost function with VVUQ verification weights

```markdown
## VVUQ Contract Log
| MathObject | Contract ID | Verdict | Verification ID | Attempts |
|---|---|---|---|---|
| quadratic_formula | contract_2a8d51b1b8b3 | ACCEPTED | verify_fb1c4e44462b4123 | 3 |
```

Hand off to developer agent for TDD implementation.

**Initiating contract-verified formalization...**
