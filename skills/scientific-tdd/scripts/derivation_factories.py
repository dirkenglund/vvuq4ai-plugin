#!/usr/bin/env python3
"""
Derivation Step Factory Functions
==================================

Reusable factory functions for creating derivation steps.
Extracted from physics_model_with_derivations.py during REFACTOR phase.

Author: Claude (Anthropic)
Date: October 28, 2025
"""

from typing import Dict, Any


def create_voltage_dependence_step() -> Dict[str, Any]:
    """
    Factory: Create step 1 - voltage dependence substitution

    Physics: In field-effect devices, carrier density depends on gate voltage.

    Returns:
        Dictionary with step metadata and transformations
    """
    return {
        'step': 1,
        'operation': 'substitute',
        'from': 'σ = n*e²*τ/m',
        'to': 'σ(V) = n(V)*e²*τ/m',
        'justification': (
            'In field-effect devices, carrier density n depends on gate voltage V. '
            'The electric field from the gate modulates the carrier concentration '
            'in the conducting channel.'
        ),
        'physics': (
            'For 2D materials like graphene, the gate capacitance C relates '
            'voltage to carrier density: n = C*(V - V_Dirac)/e, where V_Dirac '
            'is the charge neutrality point voltage.'
        )
    }


def create_linearization_step() -> Dict[str, Any]:
    """
    Factory: Create step 2 - Taylor expansion linearization

    Math: n(V) ≈ n_0 + (dn/dV)|_V0 * (V - V_0)

    Returns:
        Dictionary with linearization step
    """
    return {
        'step': 2,
        'operation': 'linearize',
        'from': 'σ(V) = n(V)*e²*τ/m',
        'to': 'σ(V) = [n_0 + α*(V - V_0)]*e²*τ/m',
        'justification': (
            'Near an operating point V_0, we linearize n(V) using Taylor expansion: '
            'n(V) ≈ n_0 + (dn/dV)|_V0 * (V - V_0), where α = (dn/dV)|_V0'
        ),
        'validity': (
            'Valid for |V - V_0| << V_0, away from charge neutrality point '
            'where n(V) has strong nonlinear behavior'
        )
    }


def create_simplification_step() -> Dict[str, Any]:
    """
    Factory: Create step 3 - parameter simplification

    Result: σ(V) = σ_0 + σ_1*(V - V_0) (linear model)

    Returns:
        Dictionary with simplification step
    """
    return {
        'step': 3,
        'operation': 'simplify',
        'from': 'σ(V) = [n_0 + α*(V - V_0)]*e²*τ/m',
        'to': 'σ(V) = σ_0 + σ_1*(V - V_0)',
        'justification': (
            'Define σ_0 = n_0*e²*τ/m (conductivity at V = V_0) and '
            'σ_1 = α*e²*τ/m (voltage-dependent coefficient)'
        ),
        'result': (
            'This gives a linear voltage-dependent conductivity model suitable '
            'for circuit analysis and device modeling.'
        )
    }


def create_drude_derivation_steps() -> list[Dict[str, Any]]:
    """
    Convenience function: Get all Drude model derivation steps.

    Returns:
        List of 3 derivation steps (voltage → linearize → simplify)
    """
    return [
        create_voltage_dependence_step(),
        create_linearization_step(),
        create_simplification_step()
    ]


# Example usage
if __name__ == "__main__":
    steps = create_drude_derivation_steps()

    print("Drude Model Derivation Steps")
    print("=" * 70)

    for step in steps:
        print(f"\nStep {step['step']}: {step['operation']}")
        print(f"  From: {step['from']}")
        print(f"  To:   {step['to']}")
        print(f"  Why:  {step['justification'][:60]}...")
