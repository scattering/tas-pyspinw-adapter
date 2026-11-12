import pytest

from tas_copilot_contracts import ToolCall, ToolResultStatus

from tas_pyspinw_adapter.copilot_plugin import run_tool


def test_optional_upstream_pyspinw_ferromagnetic_chain_smoke():
    pyspinw = pytest.importorskip("pyspinw", reason="upstream pyspinw is not installed")

    unit_cell = pyspinw.UnitCell(1, 1, 1)
    site = pyspinw.LatticeSite(0, 0, 0, 0, 0, 1, name="X")
    structure = pyspinw.Structure([site], unit_cell=unit_cell)
    exchanges = [pyspinw.HeisenbergExchange(site, site, cell_offset=(1, 0, 0), j=-1)]
    hamiltonian = pyspinw.Hamiltonian(structure, exchanges)
    path = pyspinw.Path([[0, 0, 0], [1, 0, 0]], n_points_per_segment=5)

    energies, intensities = hamiltonian.energies_and_intensities(path.q_points(), use_rust=False)

    assert energies.shape[0] == 5
    assert len(intensities) == 5


def test_optional_adapter_runs_ferromagnetic_chain():
    pytest.importorskip("pyspinw", reason="upstream pyspinw is not installed")

    result = run_tool(
        ToolCall(
            tool_namespace="tas.pyspinw",
            tool_name="run_spinwave",
            arguments={
                "model": {
                    "kind": "ferromagnetic_chain",
                    "unit_cell": [1, 1, 1],
                    "site": {"position": [0, 0, 0], "spin": [0, 0, 1], "name": "X"},
                    "exchange": {"type": "heisenberg", "cell_offset": [1, 0, 0], "j": -1},
                },
                "calculation": {"q_path": [[0, 0, 0], [1, 0, 0]], "n_points_per_segment": 5, "use_rust": False},
            },
        )
    )

    assert result.status == ToolResultStatus.success
    assert result.output["summary"] == "pySpinW ferromagnetic_chain calculation completed."
    assert result.output["simulation_only"] is True
    assert result.output["model_kind"] == "ferromagnetic_chain"
    assert result.output["q_point_count"] == 5
    assert result.output["energy_shape"][0] == 5
    assert result.output["intensity_shape"][0] == 5
