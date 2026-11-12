from __future__ import annotations

from tas_pyspinw_adapter.adaptive_counts import simulate_counts


def test_adaptive_count_boundary_returns_contract_result():
    result = simulate_counts(
        {
            "point": {
                "point_id": "q-001",
                "nodes": {"Q.H": 0.0, "Q.K": 0.0, "Q.L": 0.0, "et.deltaE": 0.0},
                "metadata": {},
            },
            "model_spec": {"background": 10.0, "count_scale": 90.0},
            "count_time": 2.0,
            "count_context": {"backend": "external_pyspinw_adapter"},
        }
    )

    assert result["expected_rate_hz"] == 100.0
    assert result["expected_counts"] == 200.0
    assert result["metadata"]["adapter"] == "tas_pyspinw_adapter.adaptive_counts"
