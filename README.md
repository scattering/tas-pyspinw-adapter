# TAS pySpinW Adapter

This repository is the TAS co-pilot plugin boundary for upstream `SpinW/pySpinW`.

Repository remote: `git@github.com:scattering/tas-pyspinw-adapter.git`

It should stay separate from:

- `tascopilot`, which owns contracts, registry, permissions, provenance, audit, catalogs, retrieval, and workflows.
- upstream `https://github.com/SpinW/pySpinW`, which owns spin-wave calculation internals.
- `tasai`, which owns model-guided spin-wave measurement planning and steering logic.

## Tool

- `tas.pyspinw.run_spinwave`

The tool is `simulation_only`. It must never issue instrument commands or represent its output as approved measurement execution.

## Current Behavior

The first adapter slice is contract-safe and fail-closed:

- If upstream `pyspinw` is not importable, it returns `ToolResult(status="unavailable")`.
- If required inputs are missing, it returns `ToolResult(status="missing_input")`.
- If `pyspinw` is importable and `model.kind == "ferromagnetic_chain"`, it runs a narrow upstream pySpinW fixture through `Hamiltonian.energies_and_intensities(...)` and returns a contract-shaped simulation summary.
- Other model shapes return a minimal simulation-boundary summary and runtime provenance until their mappings are validated.

The `ferromagnetic_chain` input is validated with `tas_copilot_contracts.SpinWaveCalculationInput` and returns fields compatible with `SpinWaveCalculationResult`.

Upstream pySpinW remains a separate dependency; this adapter does not vendor its scientific internals.

Minimal concrete input:

```json
{
  "model": {
    "kind": "ferromagnetic_chain",
    "unit_cell": [1, 1, 1],
    "site": {"position": [0, 0, 0], "spin": [0, 0, 1], "name": "X"},
    "exchange": {"type": "heisenberg", "cell_offset": [1, 0, 0], "j": -1}
  },
  "calculation": {
    "q_path": [[0, 0, 0], [1, 0, 0]],
    "n_points_per_segment": 5,
    "use_rust": false
  }
}
```

## Development

Install with the co-pilot contracts available:

```bash
pip install -e ../tascopilot-paper/packages/tas_copilot_contracts
pip install -e .
```

Run tests:

```bash
python -m pytest
```

Run tests from a real file/module context. Upstream pySpinW can use multiprocessing in the non-Rust path, so `python - <<'PY' ... PY` stdin scripts may fail because `<stdin>` is not importable as `__main__`.

Register with `tascopilot` either by editable install or:

```bash
TAS_COPILOT_PLUGIN_MODULES=tas_pyspinw_adapter.copilot_plugin
```

## Reproducibility Tests

Install the shared contracts from the
[TASCopilot paper repository](https://github.com/scattering/tascopilot-paper)
and this package into a Python 3.11 or newer environment:

```sh
TASCOPILOT_PAPER=/absolute/path/to/tascopilot-paper
python -m pip install -e "$TASCOPILOT_PAPER/packages/tas_copilot_contracts"
python -m pip install -e . pytest
python -m pytest -q -rs
```

Tests use local fixtures. Optional upstream runtimes or explicitly supplied
archive fixtures are reported as skipped when unavailable. No instrument
connection is required. No full papers, private corpus, or development
handoff documents are included.
