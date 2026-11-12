"""Adaptive count-model boundary for tasAI/NICE simulator loops.

The callable in this module is intentionally owned by the pySpinW adapter repo,
not by tascopilot core. It exposes the JSON-compatible function used by
`workflow tasai-adaptive-nice-sim --count-backend external_pyspinw_adapter`:

    simulate_counts(payload: dict) -> dict

This first implementation is a validated preview boundary. Concrete pySpinW or
SpinW calculations can replace the preview formula behind the same contract in
this repository or in a TACC/container runtime.
"""

from __future__ import annotations

from typing import Any


def simulate_counts(payload: dict[str, Any]) -> dict[str, Any]:
    from tas_copilot_contracts import AdaptiveCountRequest, AdaptiveCountResult

    request = AdaptiveCountRequest.model_validate(payload)
    nodes = request.point.nodes
    model_spec = request.model_spec
    background = float(model_spec.get("background") or 20.0)
    scale = float(model_spec.get("count_scale") or 100.0)
    h = float(nodes.get("Q.H", 0.0))
    k = float(nodes.get("Q.K", 0.0))
    l = float(nodes.get("Q.L", 0.0))
    energy = float(nodes.get("et.deltaE", 0.0))
    preview_intensity = max(0.0, 1.0 - (h * h + k * k + l * l) - 0.01 * abs(energy))
    expected_rate = background + scale * preview_intensity
    result = AdaptiveCountResult(
        expected_counts=expected_rate * request.count_time,
        expected_rate_hz=expected_rate,
        metadata={
            "adapter": "tas_pyspinw_adapter.adaptive_counts",
            "adapter_status": "validated_preview_formula",
            "upstream_pyspinw_required_for_production": True,
            "behavior_boundary": "simulation_only",
        },
    )
    return result.model_dump(mode="json")

