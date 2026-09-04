# SHARMI — Architecture

## Overview

SHARMI is designed as a modular, service-oriented decision-support system for disaster management. The architecture separates concerns into distinct engines that compose into a unified pipeline.

## Planned Components

### FastAPI API Layer

The HTTP interface for the system. Exposes REST endpoints for data ingestion, analysis requests, officer decisions, and audit queries.

**Status:** Phase 0 foundation in place.

### Risk Engine

Evaluates direct hazard exposure for geographic zones. Takes hazard data and infrastructure maps as input; outputs direct risk scores per zone.

**Status:** Planned — Phase 2.

### Cascade Engine

Models infrastructure dependencies and simulates how failure in one system triggers downstream failures. Builds a dependency graph from infrastructure data and propagates disruption events.

**Status:** Planned — Phase 3.

### Cascade Shadow Zone Identification

Identifies zones that are not directly hit by a hazard but are rendered dangerous by cascading infrastructure failures. This is SHARMI's primary differentiator.

**Status:** Planned — Phase 4.

### Time-to-Impact Estimation

Estimates how long before a cascade-affected zone becomes critical, enabling prioritized response.

**Status:** Planned — Phase 5.

### Action Engine

Generates explainable, actionable recommendations for each identified risk zone, drawing on cascade paths and time-to-impact data.

**Status:** Planned — Phase 5.

### Relocation Engine

Optimizes safe relocation routes and destinations for affected populations. Considers capacity, safety, distance, and infrastructure availability.

**Status:** Planned — Phase 6.

### Confidence Engine

Quantifies the reliability of each recommendation based on data quality, model coverage, and input completeness.

**Status:** Planned — Phase 8.

### Officer / Audit Layer

Provides override capability for field officers and logs all decisions for accountability.

**Status:** Planned — Phase 8.

### Frontend Dashboard

Visual interface for viewing risk maps, cascade simulations, recommendations, and relocation plans.

**Status:** Planned — Phase 10.

## Conceptual Data Flow

```
Hazard Event
    ↓
Direct Risk Assessment
    ↓
Infrastructure Dependency Mapping
    ↓
Cascade Simulation
    ↓
Cascade Shadow Zone Identification
    ↓
Time-to-Impact Estimation
    ↓
Action Recommendation Generation
    ↓
Relocation Optimization
    ↓
Officer Review & Decision
    ↓
Audit Log
```

Each stage feeds the next. The system is designed so components can be developed and tested independently before integration.

## Design Principles

1. **Modularity** — Each engine is a self-contained service with clear inputs/outputs.
2. **Incremental buildability** — The system is useful at every phase, not just at the end.
3. **Explainability** — Every recommendation traces back to the data and reasoning that produced it.
4. **Offline-capable** — Core analysis works without live sensor feeds (uses historical/demo data).
5. **Human-in-the-loop** — Officers can override any automated recommendation with justification.
