# Objective B — Phase 1 Foundation

This phase preserves the current B weekly surveillance behavior while making it
reusable and database-driven.

Implemented in this phase:
- B1 disease-specific surveillance (Hospital × Week × Disease)
- Daily disease aggregation available for later baseline work
- Disease-specific week-over-week growth and incidence proportion

Preserved:
- PostgreSQL source of truth
- weekly hospital encounter counts
- week-over-week growth
- existing GREEN/YELLOW/ORANGE/RED thresholds
- existing cross-hospital assessment
- optional CSV reporting

New architectural property:
- `run_foundation()` can be called by later modules or FastAPI without running
  the script as a batch job.

Not implemented yet:
- symptom-specific surveillance
- symptom-specific surveillance
- historical baselines
- deviation/anomaly scoring
- persistence
- change-point detection
- exponential growth fitting
- graph propagation
- Objective A integration
- severity burden
- composite outbreak risk
- continuous baseline updates
- controlled outbreak validation

`outbreak_detection_legacy.py` is the original uploaded implementation.
