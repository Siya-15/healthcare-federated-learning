# Running the frontend

One React + Vite + Tailwind app covering all four portals from the integration
spec: **Doctor**, **Surveillance**, **Federated & Privacy**, and **AI
Operations**. It talks to FastAPI over `/api` only — it never imports Python ML
modules and never downloads a model artifact.

## Prerequisites

- **Node 18+** (`node -v`).
- Dependencies are vendored in `node_modules/`; `npm install` only reconciles
  them with `package.json`.

## Start the dev server

```bash
cd frontend
npm install        # optional; deps are already present
npm run dev        # http://localhost:5173
```

Vite proxies every `/api` request to `http://127.0.0.1:8000` (`vite.config.js`).

## Sample-data mode is the default

There is **no backend on this branch**, so the service layer
(`src/services/*.js`) resolves **labelled fixtures** (`src/mocks/*.js`) instead
of calling the API. Every screen shows a blue "Sample data" banner. Nothing is a
real patient, hospital, or model result.

| To do this | Action |
|---|---|
| Run against a real backend on `:8000` | `VITE_USE_MOCK=0 npm run dev` |
| (live mode) if the API is briefly unreachable | it still falls back to fixtures on a `502/504`/connection error; real `403/404/422/503` are shown as errors |
| Switch portal / role | top-bar **DEMO Role** selector (persisted to `localStorage`) |
| Pick the acting hospital (doctor / hospital-admin) | top-bar **Hospital** selector |

RBAC is enforced server-side in production (spec section 16). The role switcher
is a stand-in for auth; `RoleGuard` filters navigation and shows an explicit
"access denied" panel (mirrors HTTP 403).

## Roles → portals

| Role | Portals |
|---|---|
| Doctor / Clinician | Doctor Portal |
| Hospital Administrator | Surveillance, Federated & Privacy |
| Central / Public-health Admin | Surveillance, Federated & Privacy, AI Operations |
| Technical Reviewer / Admin | Surveillance, Federated & Privacy, AI Operations |

## Production build

```bash
npm run build      # -> dist/  (git-ignored)
npm run preview     # http://localhost:4173
```

## Structure (spec section 15)

```
src/
├── app/
│   ├── router.jsx                 all routes, wrapped in AppLayout + RoleGuard
│   ├── auth/RoleContext.jsx       demo identity + portal/role map
│   └── roleGuard/RoleGuard.jsx    per-portal access gate
├── components/
│   ├── layout/AppLayout.jsx       sidebar + top bar + <Outlet>
│   ├── common/ui.jsx              Card, LevelBadge, DataState, NotImplemented, …
│   ├── tables/DataTable.jsx       generic table
│   ├── charts/TrendChart.jsx      recharts line wrapper
│   ├── clinical/                  advisor panels + PipelineStrip + EncounterForm + AdvisorView
│   └── federated/DataFlowDiagram.jsx
├── services/                      api.js + one module per portal
│   ├── api.js  clinicalApi.js  surveillanceApi.js  federatedApi.js  privacyApi.js  modelApi.js
├── mocks/                         master.js, e13Sample.js, surveillance.js, federated.js, privacy.js, models.js, encounters.js
├── hooks/useApi.js                loading / error / data / reload / isMock
├── pages/
│   ├── Home.jsx
│   ├── doctor/       Dashboard  NewEncounter  TreatmentAdvisor  EncounterHistory
│   ├── surveillance/ Overview  Alerts  EmergingSymptoms  Trends
│   ├── federated/    Overview  Hospitals  Rounds  DataFlow
│   ├── privacy/      Controls  Audit  DataMinimization
│   └── ai/           ModelOverview  Metrics  Versions  Explanations
└── types/apiSchemas.js            JSDoc typedefs for the E13 contract
```

## Endpoints the app expects (spec section 7)

```
GET  /api/clinical/dashboard
GET  /api/clinical/form-options
GET  /api/clinical/encounters                 POST /api/clinical/encounters
GET  /api/clinical/encounters/{id}
GET  /api/clinical/treatment-advisor/{id}     POST /api/clinical/treatment-advisor
GET  /api/models/explanations/{encounter}/{treatment}
GET  /api/surveillance/overview | alerts | emerging-symptoms | trends
GET  /api/federated/network | rounds | model
GET  /api/privacy/policy | data-flow | audit
GET  /api/models/overview | metrics | versions
```

When the backend is built, run it on `:8000`, start the dev server with
`VITE_USE_MOCK=0`, and no frontend change is needed. Align real responses to the
shapes in `src/mocks/*` / `src/types/apiSchemas.js` — treat the fixtures as
followers of the contract, not its source.

## Scope language (spec section 16)

- Treatment-success probabilities are model-based **observational associations**,
  not causal effect estimates.
- SHAP is **associational**, shown as explanation metadata, not a
  treatment-quality score.
- Uncertainty / recovery ranges are **model-derived predictive spreads**, not
  formal confidence intervals.
- Objective A shows **atypical symptom patterns**, never "new pathogen / variant".
- Differential privacy and secure aggregation render as `NOT_IMPLEMENTED` — the
  prototype does not do them.
- Federated metrics are reported honestly (Macro-F1 ≈ 0.058; Micro-F1
  non-monotonic across rounds).
