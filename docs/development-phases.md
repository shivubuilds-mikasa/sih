# SHARMI — Development Phases

SHARMI is being built incrementally for the SIH prototype. Each phase produces working, testable output.

## Phase Overview

| Phase | Name | Description |
|-------|------|-------------|
| 0 | Foundation | Project structure, backend scaffolding, configuration, tests |
| 1 | Demo Data & Domain Models | Sample datasets, data models, basic ingestion |
| 2 | Direct Risk Engine | Hazard-zone risk scoring using input data |
| 3 | Infrastructure Cascade Engine | Dependency graph and cascade simulation |
| 4 | Cascade Shadow Zone | Identification of indirectly-affected zones |
| 5 | Time-to-Impact & Action Engine | Impact timing and explainable recommendations |
| 6 | Relocation Optimizer | Safe relocation route and destination planning |
| 7 | Relocation Sustainability Score | Long-term viability scoring for relocation plans |
| 8 | Confidence & Officer Override | Reliability indicators and officer decision layer |
| 9 | Unified Decision API | Single endpoint composing all engines |
| 10 | Frontend Dashboard | Visual interface for exploration and decision-making |
| 11 | SIH Demo Hardening | Performance, polish, demo scenarios, stress testing |

## Key Differentiators

The following capabilities are what set SHARMI apart from standard hazard maps:

- **Cascade Shadow Zone Detection** — Finding danger zones created indirectly by infrastructure failure chains
- **Safe Relocation Optimization** — Computing viable relocation plans that account for capacity, distance, and sustainability
- **Explainable Cascade Paths** — Tracing exactly why a zone is flagged as dangerous, through every link in the failure chain

## Notes

- Each phase builds on the previous one but can be tested independently.
- Phases 0–8 are backend-focused. Phase 10 introduces the frontend.
- Phase 11 is focused on polish and demo readiness, not new features.
