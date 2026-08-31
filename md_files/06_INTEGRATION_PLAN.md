# Healthcare Project — Step-by-Step Integration Plan

Derived from `00`–`05` in this folder plus `ML/ML_handoff.md`, and checked against the actual
state of the repository on 31 August 2026.

This plan covers the work listed in `05_STATUS_REMAINING_FUTURE_SCOPE.md` §"What remains
immediately before Review 2" and the integration targets in `04_BACKEND_FRONTEND_INTEGRATION.md`.

**Governing rule** (from `05`): the ML implementation is **frozen**. Nothing below adds a model,
an algorithm or an ML feature. Phase 0 fixes packaging/path/persistence defects only — these
qualify as "an actual integration bug is found", because the backend cannot call the ML layer
without them.

---

## Reality check — five blockers the handoff docs do not mention

These were found by reading the code, not the docs. Phase 0 exists to clear them; skipping
Phase 0 will stall Phase 2.

| # | Blocker | Evidence | Consequence if ignored |
|---|---|---|---|
| B1 | ML modules are **scripts, not a library**. Each ends in `if __name__ == "__main__"`, prints to stdout and writes bare-filename CSVs into the CWD. | `outbreak_detection.py:376`, `cross_hospital_patterns.py:195`, `privacy_audit.py:354` | The backend cannot import and call them; results land in whatever directory the API server was started from. |
| B2 | **FL metrics are never persisted.** Clients compute accuracy/F1/Hamming and return them in a `MetricRecord`; the server prints "completed" and exits. | `flower_client.py:350-365`, `flower_server.py` (no write) | `GET /api/federated-learning/status` has no source of truth. The 87.82% figures currently exist **only in markdown**. |
| B3 | The `sys.path.append` in DB-connected ML modules resolves to **`ML/`, not the repo root**, so it does *not* make root-level `database.py` importable. | `outbreak_detection.py:4-10` (`dirname(dirname(__file__))`) | `from database import get_engine` fails unless the repo root is separately on `PYTHONPATH`. |
| B4 | **`patient_token` is not a database column.** It is derived in-memory inside `privacy_verification.py`; the DB stores raw `patient_id`. | `privacy_verification.py:64`, `database_writer.py:29` | `GET /api/encounters/{token}` cannot be implemented as a lookup — SHA-256 is not reversible. Needs a decision (Step 0.5). |
| B5 | **The treatment API contract does not match the function.** `04` specifies `POST /api/treatment/recommend` taking age/gender/symptoms/vitals/disease/severity; the code exposes `recommend_treatments(encounter_id)`, which loads that patient from the DB itself. | `treatment_recommender.py:247`, `04_BACKEND_FRONTEND_INTEGRATION.md:124-138` | Either the endpoint contract or an adapter has to change. Decide in Step 0.6. |

---

## Phase 0 — Make the ML layer callable *(blocks everything; no UI work depends on it)*

### 0.1 Reproducible environment
- Write `config.py` at the repo root (gitignored): `DB_CONFIG = {user, password, host, port, database}`.
- Point `datasets/knowledge tables/import_tables.py`'s env vars (`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`/`DB_NAME`, default `federatedProject_db`) at the **same** database.
- Set `PRIVACY_SECRET` in the environment — `privacy_protection.py` refuses to run without it, and the value must stay **identical** across runs or every pseudonym changes.
- Record the exact `PYTHONPATH` the backend will use (repo root **and** `ML/`), per B3.
- *Done when:* `python list_tables.py` prints the full table list from the repo root.

### 0.2 Confirm the data pipeline still runs end to end
Run in order, from the repo root: `test_loader.py` → `test_pipeline.py` → `test_database_writer.py`
→ `run_multihospital_simulation.py` → `prepare_ml_data.py`.
- Copy the regenerated `ml_data_H0XX.csv` into `ML/` as well (both copies are committed).
- *Done when:* `prepare_ml_data.py` reports "All 27 symptom columns present." for all ten hospitals.

### 0.3 Give every ML output a stable, absolute path *(fixes B1)*
Do **not** rewrite the algorithms. In each analysis script, replace the bare output filename with a
path anchored to the file, following the pattern `treatment_recommender.py:25` already uses:
```python
ML_DIR = Path(__file__).resolve().parent.parent
... .to_csv(ML_DIR / "data" / "outbreak_surveillance.csv", index=False)
```
Apply to: `outbreak_detection.py` (2 outputs), `cross_hospital_patterns.py` (2), `privacy_audit.py`,
`data_minimization.py`. Do the same for the two modules that load/save the model artifact by bare
name — `treatment_advisor.py:27` and `treatment_model.py:494` → `ML/models/treatment_success_model.pkl`.
- *Done when:* each script produces the correct file in `ML/data/` regardless of the CWD it was launched from.

### 0.4 Persist the federated-learning result *(fixes B2 — highest-risk item in Phase 0)*
- In `flower_server.py`, capture the aggregated metrics returned by `strategy.start(...)` and write
  `ML/data/fl_run_status.json`: run timestamp, rounds completed, participating hospitals,
  per-round metrics, and the final accuracy / micro-F1 / macro-F1 / Hamming loss.
- Run the federation once to generate it. Note the config traps before running: `flower_server.py`
  **hardcodes `num_rounds=3`** (it ignores `num-server-rounds`), and its `FedAvg` requires
  `min_available_nodes=10`, so the federation needs **≥10 supernodes** — the commented-out
  reference block's `num-supernodes = 3` will hang.
- Reconcile the produced numbers against the published 87.82% / 39.23% / 5.83% / 12.18%. **If they
  differ, publish the new run and say so** — `05` requires honest reporting, and macro-F1 being low
  is an expected, documented limitation, not a bug to hide.
- *Done when:* `fl_run_status.json` exists and the API can serve FL status without ever launching a
  simulation (`04` explicitly forbids running FL on dashboard open).

### 0.5 Decide the `patient_token` strategy *(fixes B4)*
Pick one and write it down:
- **(a) Persisted token column** *(recommended)* — add `patient_token` to `patient_encounter`,
  backfilled with `pseudonymize_patient_id(patient_id, PRIVACY_SECRET)`. Indexable, so
  `GET /api/encounters/{token}` is a normal lookup. Requires a schema change.
- **(b) Backend-side token map** — compute tokens for all patients at startup and hold the
  reverse map in the API process. No schema change; costs memory and rebuilds on every restart.

Whichever is chosen, the raw `patient_id` must never leave the service layer.

### 0.6 Settle the treatment-advisor contract *(fixes B5)*
- **Recommended:** keep `POST /api/treatment/recommend` accepting an `encounter_id` (matching
  `recommend_treatments`), and treat the ad-hoc age/symptoms/vitals form in `04` as a Phase 3
  stretch goal. It reuses the validated code path unchanged.
- If the ad-hoc form is required for the demo, build the adapter **in the backend**: assemble the
  `patient` dict and `patient_symptoms` set that `create_features(...)` expects and call it
  directly, bypassing `load_patient`. Do not modify the ML module.

### 0.7 Emit machine-readable privacy results
`privacy_verification.py` prints its four checks and returns a bool. Have its `__main__` also write
`ML/data/privacy_verification.json` (`{check_name: PASS|FAIL}` × 4) so `GET /api/privacy/status`
reads a file instead of scraping stdout.

---

## Phase 1 — Service layer *(backend; depends on Phase 0)*

`05` asks for a "service/interface layer". The repo already has the right homes for it, and they are
**empty files** today: `services/lookup_service.py`, `services/postgres_loader.py`, and `main.py`
(despite `02_REPOSITORY_FILE_GUIDE.md` describing them as working components).

Build one Python package that the API imports, exposing plain functions that return
dicts/DataFrames — no printing, no `sys.exit`, no CWD assumptions:

| Service | Wraps | Returns |
|---|---|---|
| `surveillance_service` | `ML/data/weekly_hospital_cases.csv`, `outbreak_surveillance.csv` | per-hospital cases, growth rate, alert level, overall level, affected-hospital % |
| `patterns_service` | `hospital_symptom_pattern_counts.csv`, `cross_hospital_symptom_patterns.csv` | emerging/recurring and cross-hospital patterns |
| `fl_service` | `ML/data/fl_run_status.json` (Step 0.4) | latest round, status, global metrics — **never triggers a run** |
| `treatment_service` | `treatment_recommender.recommend_treatments` | ranked treatments + success probability, recovery days, risks |
| `privacy_service` | `privacy_audit.csv`, `data_minimization_matrix.csv`, `privacy_verification.json` | 46 audited columns, minimization matrix, 4 PASS checks |
| `encounter_service` | `database.py` + the Step 0.5 token strategy | tokenized encounter records |
| `lookup_service` | `loader.load_all_tables()` | hospital/disease/symptom/severity reference data |

**Two invariants enforced here, not in the API layer:**
1. `patient_id` is stripped before any value is returned.
2. Surveillance returns hospital-level or pattern-level aggregates only — never individual rows.

Cache the CSV/JSON reads at startup; these are batch artifacts, not live queries.

---

## Phase 2 — Backend API *(depends on Phase 1)*

Implement the eight targets from `04` in this order — each is unblocked by the phase above it, and
the first three carry the demo:

1. `GET /api/hospitals` — smallest end-to-end slice; proves config, DB and service wiring.
2. `GET /api/surveillance` — hospital ID, current/previous cases, growth rate, alert level, overall
   level, outbreak signal, affected %, emerging + cross-hospital patterns.
3. `GET /api/federated-learning/status` — 10 hospitals, H001–H010 participation, 3 completed
   rounds, FedAvg, global metrics, read from the stored artifact.
4. `POST /api/treatment/recommend` — per the Step 0.6 contract. Every response must be labelled
   **clinical decision support, not autonomous prescription**.
5. `GET /api/privacy/status` — 46 columns, classification, minimization matrix, 4 PASS checks.
6. `GET /api/encounters/{token}` — token-addressed only.
7. `GET /api/dashboard` — composes 2/3/5 plus a recent-pattern summary. Serve from cached
   artifacts; it must not fan out into expensive work on every load.
8. `POST /api/encounters` — **last, and optional for Review 2.** `DatabaseWriter.save()` expects a
   fully-populated `Encounter` object produced by the generator pipeline, so accepting one from
   JSON needs a construction path that does not exist yet. Cut this first if time runs short.

**Cross-cutting:** a JSON error shape, CORS for the frontend, and a response filter that rejects any
payload containing `patient_id` (belt-and-braces over the Phase 1 invariant).

---

## Phase 3 — Frontend *(the six views from `04`; depends on Phase 2)*

Frontend consumes backend JSON **only** — no PostgreSQL connection, no importing Python modules.

Build in this order so each view lands on an endpoint that already exists:

1. **Surveillance** — table + case-growth and alert-distribution charts. Colour by GREEN / YELLOW / ORANGE / RED.
2. **Federated Learning** — the `Local Data → Local Training → Model Update → FedAvg → Global Model`
   flow, 10-hospital participation, 3 rounds, and the four global metrics. Display the banner
   **"Raw patient data remains at hospital level."** Do **not** label anything as differential
   privacy or secure aggregation — neither is implemented.
3. **Treatment Advisor** — input form → ranked options with success probability, priority /
   first-line / referral metadata, expected recovery days, and complication risks. Persistent
   "decision support, not prescription" notice.
4. **Privacy / Audit** — 46 audited columns, classification, minimization matrix, four PASS checks.
5. **Clinical / Patient** — token, age, gender, symptoms, vitals (temp, HR, RR, systolic/diastolic
   BP, SpO₂), disease, severity, admission/visit/discharge, onset/travel/vaccination. Header shows
   the **token**; raw patient IDs must not appear anywhere in the DOM.
6. **Dashboard** — built last, once the underlying views exist: 10 hospitals monitored, outbreak
   status, RED-alert hospitals, affected %, latest FL round + metrics, privacy status, recent
   pattern summary.

---

## Phase 4 — Joint verification *(`05` §Joint)*

1. **End-to-end privacy enforcement audit.** Run `privacy_enforcement_audit.py`, then verify by
   inspection: no raw `patient_id` in any API response, any dashboard, or any chart tooltip; all
   surveillance output aggregated; FL exchanges model parameters only.
2. **Complete application workflow.** Walk the full path: encounter in the DB → pseudonymized
   clinical view → treatment recommendation → surveillance alert → FL status → privacy PASS.
3. **Integration testing.** Cover the failure modes this stack actually has: API started from the
   wrong working directory, missing/rotated `PRIVACY_SECRET` (tokens silently change), stale
   `ML/data/*.csv` after a re-simulation, and an unknown token or encounter ID.
4. **Claim review against `01` §"Prototype vs production".** Confirm the UI claims none of:
   national-scale deployment, differential privacy, secure aggregation, production encryption/RBAC,
   HMIS integration, transformer/GNN, SHAP, FedProx/FedNova, model versioning.

---

## Phase 5 — Review 2 demonstration

Follow the running order in `04` §"Recommended Review 2 demo": Dashboard → pseudonymized clinical
encounter → Treatment Advisor → surveillance/outbreak status → FL across 10 hospitals with metrics
→ privacy/audit PASS → closing explanation of local data protection and collaborative aggregation.

Prepare the slides and script around the status statement at the end of `05`. Two honesty
requirements carried over from the handoff:
- Report FL metrics as they are — **macro-F1 5.83% is low and micro-F1 did not improve
  monotonically.** State it as a known limitation of the prototype.
- Present the treatment model as it validated: accuracy 0.8799, **ROC-AUC 0.6317** on 14,165
  records with a leakage-aware encounter-level split.

Have a fallback for the FL segment: show the stored `fl_run_status.json` result rather than running
a live federation during the review.

---

## Sequencing summary

```text
Phase 0  Make ML callable      ── blocks everything
   │     0.1 env  0.2 pipeline  0.3 paths  0.4 FL artifact  0.5 token  0.6 contract  0.7 privacy json
   ▼
Phase 1  Service layer         ── fills the empty services/
   ▼
Phase 2  Backend API           ── 8 endpoints, demo-critical first
   ▼
Phase 3  Frontend              ── 6 views, dashboard last
   ▼
Phase 4  Joint verification    ── privacy audit, workflow, integration tests, claim review
   ▼
Phase 5  Review 2 demo
```

Phase 3 can start against mocked JSON as soon as the Phase 2 response shapes are agreed, which is
the main available parallelism. **Steps 0.4, 0.5 and 0.6 should be settled first** — each one
changes a contract that both the backend and the frontend depend on.

## Explicitly out of scope

Everything under `05` §Future scope: differential privacy, secure multiparty aggregation,
production encryption, RBAC, audit logging, FedProx/FedNova, gradient compression, async
participation, model versioning, transformers, GNNs, time-series models, SHAP/attention,
advanced anomaly detection, advanced epidemiological modelling, HMIS integration, Docker,
mobile/offline deployment, batch uploads, large-scale rollout.

Do not add these for Review 2, and do not present them as implemented.
