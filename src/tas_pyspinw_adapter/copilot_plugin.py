from __future__ import annotations

from importlib import import_module, metadata
from typing import Any


TOOL_NAME = "run_spinwave"
COUNT_TOOL_NAME = "simulate_counts"
TOOL_NAMESPACE = "tas.pyspinw"
TOOL_VERSION = "0.1.0"
UPSTREAM_REPO = "https://github.com/SpinW/pySpinW"


def get_tool_specs():
    from tas_copilot_contracts import Availability, ImplementationType, PermissionLevel, SideEffectLevel, ToolSpec

    return [
        ToolSpec(
            name=TOOL_NAME,
            namespace=TOOL_NAMESPACE,
            version=TOOL_VERSION,
            description="Run spin-wave calculations through the separate pySpinW adapter boundary.",
            input_schema={
                "type": "object",
                "required": ["model"],
                "properties": {
                    "model": {"type": "object"},
                    "calculation": {"type": "object"},
                    "dry_run": {"type": "boolean"},
                },
            },
            output_schema={"type": "object"},
            side_effect_level=SideEffectLevel.simulation,
            availability=Availability.available,
            implementation_type=ImplementationType.python_entrypoint,
            required_dependencies=["tas-pyspinw-adapter", f"pyspinw from {UPSTREAM_REPO}"],
            preconditions=["SpinWaveModelSpec-compatible model input is supplied.", "Simulation only."],
            postconditions=["SpinWaveCalculationResult-compatible summary or typed unavailable/missing_input result is returned."],
            provenance_policy="Record model spec keys, adapter version, upstream pySpinW version when available, and runtime summary.",
            permissions_required=[PermissionLevel.simulation_only],
            enabled_by_default=True,
            owner_repo="git@github.com:scattering/tas-pyspinw-adapter.git",
            documentation_url=UPSTREAM_REPO,
            maintainer="William Ratcliff",
        ),
        ToolSpec(
            name=COUNT_TOOL_NAME,
            namespace=TOOL_NAMESPACE,
            version=TOOL_VERSION,
            description="Simulate expected counts for adaptive TAS planning through the pySpinW adapter boundary.",
            input_schema={
                "type": "object",
                "required": ["point"],
                "properties": {
                    "point": {"type": "object"},
                    "model_spec": {"type": "object"},
                    "count_time": {"type": "number"},
                    "count_context": {"type": "object"},
                },
            },
            output_schema={"type": "object"},
            side_effect_level=SideEffectLevel.simulation,
            availability=Availability.available,
            implementation_type=ImplementationType.python_entrypoint,
            required_dependencies=["tas-pyspinw-adapter", "tas-copilot-contracts"],
            preconditions=["AdaptiveCountRequest-compatible payload is supplied.", "Simulation only."],
            postconditions=["AdaptiveCountResult-compatible expected count overlay is returned."],
            provenance_policy="Record adapter version, model keys, point id, and simulation boundary metadata.",
            permissions_required=[PermissionLevel.simulation_only],
            enabled_by_default=True,
            owner_repo="git@github.com:scattering/tas-pyspinw-adapter.git",
            documentation_url=UPSTREAM_REPO,
            maintainer="William Ratcliff",
        ),
    ]


def run_tool(call):
    from tas_copilot_contracts import ProvenanceRecord, ToolError, ToolResult, ToolResultStatus

    if call.tool_namespace == TOOL_NAMESPACE and call.tool_name == COUNT_TOOL_NAME:
        return _run_count_tool(call)

    if (call.tool_namespace, call.tool_name) != (TOOL_NAMESPACE, TOOL_NAME):
        return ToolResult(
            status=ToolResultStatus.validation_failed,
            errors=[ToolError(code="unknown_tool", message=f"Unknown pySpinW adapter tool {call.tool_namespace}.{call.tool_name}")],
            tool_name=call.tool_name,
            tool_namespace=call.tool_namespace,
            tool_version=TOOL_VERSION,
        )

    model = call.arguments.get("model")
    if not model:
        return ToolResult(
            status=ToolResultStatus.missing_input,
            errors=[ToolError(code="missing_model", message="model is required for tas.pyspinw.run_spinwave")],
            tool_name=TOOL_NAME,
            tool_namespace=TOOL_NAMESPACE,
            tool_version=TOOL_VERSION,
        )

    pyspinw = _import_pyspinw()
    if pyspinw is None:
        return ToolResult(
            status=ToolResultStatus.unavailable,
            errors=[
                ToolError(
                    code="pyspinw_unavailable",
                    message="upstream pyspinw is not importable; install pySpinW separately and keep this adapter as the co-pilot boundary",
                    details={"upstream_repo": UPSTREAM_REPO},
                )
            ],
            provenance=[ProvenanceRecord(source_type="tool", source_id="tas-pyspinw-adapter", method="dependency_check")],
            tool_name=TOOL_NAME,
            tool_namespace=TOOL_NAMESPACE,
            tool_version=TOOL_VERSION,
            runtime_environment=_runtime_environment(None),
        )

    model_kind = model.get("kind") if isinstance(model, dict) else None
    if model_kind == "ferromagnetic_chain":
        try:
            output = _run_ferromagnetic_chain(call.arguments, pyspinw)
            warnings = ["Simulation-only pySpinW calculation; this result is not an approved instrument operation."]
        except ValueError as exc:
            return ToolResult(
                status=ToolResultStatus.validation_failed,
                errors=[ToolError(code="invalid_ferromagnetic_chain_input", message=str(exc))],
                provenance=[ProvenanceRecord(source_type="tool", source_id="tas-pyspinw-adapter", method="input_validation")],
                tool_name=TOOL_NAME,
                tool_namespace=TOOL_NAMESPACE,
                tool_version=TOOL_VERSION,
                runtime_environment=_runtime_environment(pyspinw),
            )
        except Exception as exc:
            return ToolResult(
                status=ToolResultStatus.error,
                errors=[
                    ToolError(
                        code="pyspinw_execution_error",
                        message="upstream pySpinW failed while running the ferromagnetic_chain fixture",
                        details={"exception_type": exc.__class__.__name__, "exception": str(exc)},
                    )
                ],
                provenance=[ProvenanceRecord(source_type="tool", source_id="tas-pyspinw-adapter", method="run_ferromagnetic_chain")],
                tool_name=TOOL_NAME,
                tool_namespace=TOOL_NAMESPACE,
                tool_version=TOOL_VERSION,
                runtime_environment=_runtime_environment(pyspinw),
            )
    else:
        output = _simulation_boundary_output(call.arguments, pyspinw)
        warnings = [
            "Simulation-only adapter boundary; this result is not an approved instrument operation.",
            "Only model.kind='ferromagnetic_chain' currently runs a concrete pySpinW calculation.",
        ]
    return ToolResult(
        status=ToolResultStatus.success,
        output=output,
        warnings=warnings,
        provenance=[ProvenanceRecord(source_type="tool", source_id="tas-pyspinw-adapter", method="run_spinwave")],
        tool_name=TOOL_NAME,
        tool_namespace=TOOL_NAMESPACE,
        tool_version=TOOL_VERSION,
        runtime_environment=_runtime_environment(pyspinw),
    )


def _run_count_tool(call):
    from tas_copilot_contracts import ProvenanceRecord, ToolError, ToolResult, ToolResultStatus
    from tas_pyspinw_adapter.adaptive_counts import simulate_counts

    try:
        output = simulate_counts(call.arguments)
    except ValueError as exc:
        return ToolResult(
            status=ToolResultStatus.validation_failed,
            errors=[ToolError(code="invalid_adaptive_count_input", message=str(exc))],
            provenance=[ProvenanceRecord(source_type="tool", source_id="tas-pyspinw-adapter", method="simulate_counts_validation")],
            tool_name=COUNT_TOOL_NAME,
            tool_namespace=TOOL_NAMESPACE,
            tool_version=TOOL_VERSION,
            runtime_environment=_runtime_environment(_import_pyspinw()),
        )
    return ToolResult(
        status=ToolResultStatus.success,
        output=output,
        warnings=["Simulation-only count overlay; this result is not an approved instrument operation."],
        provenance=[ProvenanceRecord(source_type="tool", source_id="tas-pyspinw-adapter", method="simulate_counts")],
        tool_name=COUNT_TOOL_NAME,
        tool_namespace=TOOL_NAMESPACE,
        tool_version=TOOL_VERSION,
        runtime_environment=_runtime_environment(_import_pyspinw()),
    )


def _import_pyspinw() -> Any | None:
    for module_name in ["pyspinw", "spinw"]:
        try:
            return import_module(module_name)
        except ImportError:
            continue
    return None


def _simulation_boundary_output(arguments: dict[str, Any], pyspinw: Any) -> dict[str, Any]:
    model = arguments.get("model") or {}
    calculation = arguments.get("calculation") or {}
    return {
        "summary": "pySpinW is importable; adapter boundary accepted the simulation request.",
        "simulation_only": True,
        "model_keys": sorted(model.keys()),
        "calculation_keys": sorted(calculation.keys()),
        "upstream_module": getattr(pyspinw, "__name__", pyspinw.__class__.__name__),
        "upstream_version": _module_version(pyspinw),
        "spectra_refs": [],
    }


def _run_ferromagnetic_chain(arguments: dict[str, Any], pyspinw: Any) -> dict[str, Any]:
    from tas_copilot_contracts import SpinWaveCalculationInput

    model = arguments.get("model") or {}
    calculation = arguments.get("calculation") or {}
    request = SpinWaveCalculationInput(model=model, **calculation)
    model_spec = request.model

    unit_cell_values = model_spec.unit_cell or [1.0, 1.0, 1.0]
    site_values = model_spec.site
    exchange_values = model_spec.exchange
    if site_values is None or exchange_values is None:
        raise ValueError("ferromagnetic_chain requires site and exchange")

    unit_cell = pyspinw.UnitCell(*unit_cell_values)
    site = pyspinw.LatticeSite(*site_values.position, *site_values.spin, name=site_values.name)
    structure = pyspinw.Structure([site], unit_cell=unit_cell)
    exchanges = [pyspinw.HeisenbergExchange(site, site, cell_offset=tuple(exchange_values.cell_offset), j=exchange_values.j)]
    hamiltonian = pyspinw.Hamiltonian(structure, exchanges)
    path = pyspinw.Path(request.q_path, n_points_per_segment=request.n_points_per_segment)
    q_points = path.q_points()
    energies, intensities = hamiltonian.energies_and_intensities(q_points, use_rust=request.use_rust)

    return {
        "summary": "pySpinW ferromagnetic_chain calculation completed.",
        "simulation_only": True,
        "model_kind": "ferromagnetic_chain",
        "q_point_count": len(q_points),
        "energy_shape": _shape(energies),
        "intensity_shape": _shape(intensities),
        "energy_preview": _preview(energies),
        "intensity_preview": _preview(intensities),
        "calculation": {
            "q_path": request.q_path,
            "n_points_per_segment": request.n_points_per_segment,
            "use_rust": request.use_rust,
        },
        "upstream_module": getattr(pyspinw, "__name__", pyspinw.__class__.__name__),
        "upstream_version": _module_version(pyspinw),
        "spectra_refs": [],
    }


def _shape(value: Any) -> list[int]:
    shape = getattr(value, "shape", None)
    if shape is not None:
        return [int(item) for item in shape]
    if isinstance(value, list):
        if value and hasattr(value[0], "__len__") and not isinstance(value[0], (str, bytes)):
            return [len(value), len(value[0])]
        return [len(value)]
    return []


def _preview(value: Any, limit: int = 3) -> list[Any]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, list):
        return [value]
    return [_jsonable(item) for item in value[:limit]]


def _jsonable(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return _jsonable(value.tolist())
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if hasattr(value, "item"):
        return _jsonable(value.item())
    return value


def _runtime_environment(pyspinw: Any | None) -> dict[str, Any]:
    return {
        "adapter": "tas-pyspinw-adapter",
        "adapter_version": TOOL_VERSION,
        "upstream_repo": UPSTREAM_REPO,
        "pyspinw_importable": pyspinw is not None,
        "pyspinw_module": getattr(pyspinw, "__name__", None) if pyspinw is not None else None,
        "pyspinw_version": _module_version(pyspinw) if pyspinw is not None else None,
    }


def _module_version(module: Any | None) -> str | None:
    if module is None:
        return None
    version = getattr(module, "__version__", None)
    if version:
        return str(version)
    name = getattr(module, "__name__", None)
    if not name:
        return None
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None
