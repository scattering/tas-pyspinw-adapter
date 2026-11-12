import sys
import types

from tas_copilot_contracts import ToolCall, ToolResultStatus

import tas_pyspinw_adapter.copilot_plugin as plugin
from tas_pyspinw_adapter.copilot_plugin import get_tool_specs, run_tool


def test_tool_spec_is_simulation_only():
    specs = get_tool_specs()

    assert len(specs) == 2
    spec = next(item for item in specs if item.name == "run_spinwave")
    assert spec.namespace == "tas.pyspinw"
    assert spec.name == "run_spinwave"
    assert [permission.value for permission in spec.permissions_required] == ["simulation_only"]
    assert spec.enabled_by_default is True

    count_spec = next(item for item in specs if item.name == "simulate_counts")
    assert count_spec.namespace == "tas.pyspinw"
    assert [permission.value for permission in count_spec.permissions_required] == ["simulation_only"]


def test_missing_model_returns_missing_input():
    result = run_tool(ToolCall(tool_namespace="tas.pyspinw", tool_name="run_spinwave", arguments={}))

    assert result.status == ToolResultStatus.missing_input
    assert result.errors[0].code == "missing_model"


def test_missing_pyspinw_returns_unavailable(monkeypatch):
    monkeypatch.delitem(sys.modules, "pyspinw", raising=False)
    monkeypatch.delitem(sys.modules, "spinw", raising=False)

    def import_missing(name):
        if name in {"pyspinw", "spinw"}:
            raise ImportError(name)
        return __import__(name)

    monkeypatch.setattr(plugin, "import_module", import_missing)

    result = run_tool(ToolCall(tool_namespace="tas.pyspinw", tool_name="run_spinwave", arguments={"model": {"material": "fixture"}}))

    assert result.status == ToolResultStatus.unavailable
    assert result.errors[0].code == "pyspinw_unavailable"
    assert result.runtime_environment["pyspinw_importable"] is False


def test_importable_pyspinw_returns_simulation_boundary(monkeypatch):
    fake = types.ModuleType("pyspinw")
    fake.__version__ = "0.test"
    monkeypatch.setitem(sys.modules, "pyspinw", fake)

    result = run_tool(
        ToolCall(
            tool_namespace="tas.pyspinw",
            tool_name="run_spinwave",
            arguments={"model": {"material": "fixture", "model_parameters": {}}, "calculation": {"q_path": []}},
        )
    )

    assert result.status == ToolResultStatus.success
    assert result.output["simulation_only"] is True
    assert result.output["upstream_module"] == "pyspinw"
    assert result.output["upstream_version"] == "0.test"
    assert result.runtime_environment["pyspinw_importable"] is True


def test_unknown_tool_validation_failed():
    result = run_tool(ToolCall(tool_namespace="tas.pyspinw", tool_name="other", arguments={"model": {}}))

    assert result.status == ToolResultStatus.validation_failed


def test_simulate_counts_tool_returns_count_overlay():
    result = run_tool(
        ToolCall(
            tool_namespace="tas.pyspinw",
            tool_name="simulate_counts",
            arguments={
                "point": {"point_id": "q-001", "nodes": {"Q.H": 0.0}, "metadata": {}},
                "model_spec": {"background": 10.0, "count_scale": 90.0},
                "count_time": 2.0,
            },
        )
    )

    assert result.status == ToolResultStatus.success
    assert result.output["expected_counts"] == 200.0
