# RESQML 2.0.1 ↔ 2.2 Converter

Two-way converter between RESQML 2.0.1 (EML 2.0) and RESQML 2.2 (EML 2.3) with complete object support,
including EPC+HDF5 dataspace handling and validation via Geosiris energyml.

## Features

- **Complete object support**: Features, Interpretations, Representations, Properties, CRS, TimeSeries, Activities
- **Two-way conversion**: 2.0.1 → 2.2 and 2.2 → 2.0.1
- **EPC dataspace**: Reads and writes standard EPC packages (ZIP with XML + HDF5 references)
- **HDF5 passthrough**: Array data in HDF5 is preserved/remapped between versions
- **Validation**: Uses `energyml-utils` validation to verify output conformance
- **CLI**: Simple command-line interface for batch conversion

## Supported Object Types

### Features
- GeneticBoundaryFeature / BoundaryFeature (horizons, faults, geobodies)
- TectonicBoundaryFeature / BoundaryFeature
- OrganizationFeature / Model
- GeologicUnitFeature / RockVolumeFeature
- WellboreFeature
- SeismicLatticeFeature

### Interpretations
- HorizonInterpretation
- FaultInterpretation
- GeobodyInterpretation, GeobodyBoundaryInterpretation
- WellboreInterpretation
- StratigraphicUnitInterpretation
- StructuralOrganizationInterpretation
- EarthModelInterpretation
- RockFluidOrganizationInterpretation, RockFluidUnitInterpretation
- FluidBoundaryInterpretation
- StratigraphicColumnRankInterpretation

### Representations
- TriangulatedSetRepresentation
- Grid2dRepresentation
- IjkGridRepresentation
- UnstructuredGridRepresentation
- WellboreTrajectoryRepresentation
- WellboreFrameRepresentation
- BlockedWellboreRepresentation
- PointSetRepresentation
- PolylineRepresentation, PolylineSetRepresentation
- GridConnectionSetRepresentation
- SealedSurfaceFrameworkRepresentation
- SubRepresentation

### Properties
- ContinuousProperty
- DiscreteProperty (CategoricalProperty in 2.0.1)
- PropertyKind

### Other
- LocalDepth3dCrs / LocalEngineeringCompoundCrs
- TimeSeries
- ActivityTemplate, Activity
- StratigraphicColumn
- EpcExternalPartReference (HDF5 proxy)

## Installation

```bash
pip install -e .
```

## Usage

### CLI

```bash
# Convert 2.0.1 to 2.2
resqml-convert --input model_201.epc --output model_22.epc --target-version 2.2

# Convert 2.2 to 2.0.1
resqml-convert --input model_22.epc --output model_201.epc --target-version 2.0.1

# With validation
resqml-convert --input model_201.epc --output model_22.epc --target-version 2.2 --validate
```

### Python API

```python
from resqml_converter import convert_epc

# Convert 2.0.1 -> 2.2
errors = convert_epc("input_201.epc", "output_22.epc", target_version="2.2", validate=True)

# Convert 2.2 -> 2.0.1
errors = convert_epc("input_22.epc", "output_201.epc", target_version="2.0.1", validate=True)
```

## Architecture

```
src/resqml_converter/
├── __init__.py          # Public API
├── cli.py               # Command-line interface
├── converter.py         # Main conversion orchestrator
├── epc_io.py            # EPC read/write with energyml
├── validation.py        # Energyml validation wrapper
├── mappings/
│   ├── __init__.py
│   ├── base.py          # Base mapper infrastructure
│   ├── crs.py           # CRS conversion
│   ├── features.py      # Feature type mappings
│   ├── interpretations.py  # Interpretation mappings
│   ├── representations.py  # Representation mappings
│   ├── properties.py    # Property mappings
│   └── common.py        # EML common object mappings (Citation, DOR, arrays)
```
