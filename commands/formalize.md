---
name: formalize
description: "Interactive formalization — extract equations, constraints, and test predicates from papers or design goals, then generate a verified specification"
argument-hint: "<paper/goal description> [domain]"
allowed-tools: ["Task", "Read", "Write", "Edit", "MultiEdit", "Grep", "Glob", "TodoWrite", "Bash", "WebFetch"]
---

# /formalize — Interactive Specification from Source

Generate a formal, testable specification from a paper, design goal, or requirements document. Produces SPEC.md with MathObjects, test predicates, and a cost function — then verifies key claims via VVUQ.

## Usage

```bash
/vvuq4ai:formalize "Fabry-Perot cavity with finesse >100"
/vvuq4ai:formalize "squeezed light interferometer from arxiv:2301.12345"
/vvuq4ai:formalize "RC low-pass filter with 1kHz cutoff" circuit
```

## Domains

- `general` (default) — any STEM specification
- `photonic` — waveguides, resonators, interferometers
- `circuit` — electronic circuits, impedance, SPICE
- `optimization` — constrained optimization, cost functions
- `mathematics` — formal proofs, identities

## Execute

**Description**: $ARGUMENTS

Starting interactive formalization...

### Phase 1: Source Ingestion

1. Parse source document (PDF, paper, or user description)
2. Extract equations, assumptions, key claims, figure data
3. Identify domain and relevant physics/engineering constraints
4. Search VVUQ knowledge base for related verified facts:
   ```
   vvuq_resolve(query="<key equation or claim from source>")
   ```

### Phase 2: Interactive MathObject Identification

For each equation/relationship found, propose a MathObject:

```
MathObject: <name>
  Symbol: <symbol>
  LaTeX: <equation>
  Python: <expression>
  Units: <pint units>
  Bounds: (<min>, <max>)
  Source: <paper ref or "design goal">
```

Present each to user for confirmation. Ask clarifying questions one at a time.

### Phase 3: Constraint Classification

Classify all constraints:
- **Hard constraints**: Physical laws (energy conservation, unitarity, causality)
- **Soft constraints**: Design targets (bandwidth > X, loss < Y)
- **Parameter bounds**: Valid ranges for each variable

### Phase 4: Test Predicate Generation

Generate failing tests (RED phase) from the specification:

```python
# Explicit tests — from paper figures/equations
def test_resonance_at_expected_wavelength():
    """Source: Fig. 3, λ_res = 1550.2 nm"""
    ...

# Implicit tests — internal consistency
def test_energy_conservation():
    """Physics: |S11|² + |S21|² ≤ 1"""
    ...

# VVUQ-verified tests — checked against knowledge base
def test_physical_constants_correct():
    """VVUQ: speed of light, Planck's constant"""
    ...
```

### Phase 5: Cost Function

Define weighted cost function from test predicates:

```python
cost_function = {
    "hard_constraints": {"energy_conservation": 1.0},
    "primary_objectives": {"fig3_agreement": 2.0},
    "secondary_objectives": {"bandwidth_target": 0.5},
}
```

### Phase 6: VVUQ Verification of Spec

Verify key claims in the specification:
```
vvuq_resolve(query="<each key equation/constant in spec>")
```

Flag any discrepancies before handing off to implementation.

### Phase 7: Output

Generate:
1. `SPEC.md` — human-readable specification
2. `tests/test_spec.py` — failing tests (RED state)
3. Cost function definition

Hand off to developer agent for TDD implementation.

**Initiating interactive formalization...**
