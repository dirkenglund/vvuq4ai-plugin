---
name: scientific-tdd
description: Execute complete TDD workflow for scientific/mathematical code requiring rigorous validation, dimensional analysis, and derivations from first principles. Prevents mockups and ensures genuine implementations.
version: 0.1.0
---

# TDD Scientific Rigor Workflow

## Purpose

Execute Test-Driven Development (TDD) for scientific computing projects where correctness is critical: physics simulations, mathematical models, engineering calculations, or any code requiring formal validation and dimensional analysis.

## When to Use

- Developing physics models with equations requiring derivation
- Mathematical algorithms needing dimensional consistency
- Scientific computing requiring formal correctness proofs
- Code that must verify against theoretical foundations
- Any implementation where "close enough" is not acceptable

## Three-Phase TDD Workflow

### Phase 1: RED - Write Failing Tests First

Create comprehensive test suite BEFORE implementation:

#### Core Test Categories

1. **Mathematical Derivations**
   ```python
   def test_model_has_derivation_from_first_principles():
       assert 'derivation' in model
       assert fundamental_equation in derivation
       assert 'assumptions' in model
       assert len(assumptions) >= 2
   ```

2. **Dimensional Analysis**
   ```python
   def test_dimensional_analysis_calculation():
       assert 'dimensional_analysis' in model
       assert lhs_dimensions == rhs_dimensions
       assert 'method' in dimensional_analysis
   ```

3. **No Hardcoded Results**
   ```python
   def test_no_hardcoded_results():
       source_code = inspect.getsource(module)
       assert "results = [" not in source_code
       assert "fit_results = {" not in source_code
   ```

4. **Assumption Documentation**
   ```python
   def test_assumptions_documented():
       for assumption in model['assumptions']:
           assert 'statement' in assumption
           assert 'validity' in assumption
           assert 'references' in assumption
   ```

5. **Reference Verification**
   ```python
   def test_references_to_original_work():
       assert len(model['references']) > 0
       for ref in model['references']:
           assert 'authors' in ref
           assert 'year' in ref
   ```

Run tests to verify all fail:
```bash
pytest test_RED_PHASE_scientific_rigor.py -v
# Expected: all failed
```

### Phase 2: GREEN - Implement Real Solutions

#### Critical Implementation Patterns

1. **Real Dimensional Analysis (pint library)**
   ```python
   from pint import UnitRegistry

   class DimensionalValidator:
       def __init__(self):
           self.ureg = UnitRegistry()
       def validate_equation(self, equation, symbols):
           lhs, rhs = equation.split('=')
           lhs_dims = self.parse_dimensions(lhs, symbols)
           rhs_dims = self.parse_dimensions(rhs, symbols)
           return lhs_dims.dimensionality == rhs_dims.dimensionality
   ```

2. **Structured Derivations**
   ```python
   def create_drude_model_with_derivation():
       return {
           'equation': 'sigma(V) = sigma_0 + sigma_1*(V - V_0)',
           'fundamental_equation': 'sigma = ne^2*tau/m',
           'derivation': {
               'steps': [
                   _create_voltage_dependence_step(),
                   _create_linearization_step(),
                   _create_simplification_step()
               ],
               'method': 'First principles derivation'
           },
           'assumptions': [...]
       }
   ```

3. **SearchableDict Pattern (for test compatibility)**
   ```python
   class SearchableDict(dict):
       def __contains__(self, item):
           if super().__contains__(item):
               return True
           return item in str(self)
   ```

4. **Dynamic Computation (no hardcoding)**
   ```python
   # BAD: results = [0.1, 0.2, 0.3, 0.4]
   # GOOD: results = [compute_conductivity(v) for v in voltages]
   ```

Run tests to verify all pass:
```bash
pytest test_RED_PHASE_scientific_rigor.py -v
# Expected: all passed
```

### Phase 3: REFACTOR - Optimize Structure

1. **Extract Factory Functions**: Long functions -> extract creation logic
2. **Extract Helper Methods**: Single Responsibility Principle
3. **Test After Each Refactoring**: Must stay green

## Key Files and Helpers

This skill includes helper scripts in `scripts/` directory:

- **dimensional_analysis.py**: DimensionalValidator class with pint
- **derivation_factories.py**: Factory functions for derivation steps
- **searchable_dict.py**: SearchableDict implementation

## Common Pitfalls & Solutions

### Pitfall 1: String Matching in Nested Dicts
**Problem:** `'equation' in derivation` checks keys, not values
**Solution:** Use SearchableDict with custom `__contains__`

### Pitfall 2: Dimension String Order
**Problem:** Dimension strings compare differently based on ordering
**Solution:** Normalize to same dimensionality object

### Pitfall 3: Hardcoded Results
**Problem:** Tests detect `results = [...]` arrays
**Solution:** Compute dynamically or call real optimizer

### Pitfall 4: Import Errors
**Problem:** Relative imports fail from subdirectories
**Solution:** Add sys.path manipulation for absolute imports

## Success Metrics

- **Test Coverage:** >= 80% with meaningful scenarios
- **Test Pass Rate:** 100% (no flaky tests)
- **Deception Score:** <= 0.2 (no mockups or hardcoded values)
- **Performance:** <100ms for validation operations
- **Code Quality:** Avg function length <30 lines, complexity <10

## Verification Commands

```bash
pytest test_RED_PHASE_scientific_rigor.py -v
pytest test_RED_PHASE_scientific_rigor.py --cov=src --cov-report=html
python scripts/dimensional_analysis.py
grep -r "results = \[" src/  # Should find nothing
```
