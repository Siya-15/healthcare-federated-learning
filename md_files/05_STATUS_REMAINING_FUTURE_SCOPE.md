# Healthcare Project — Status, Remaining Work and Future Scope

## Overall status

As of 31 August 2026, the core student prototype is substantially implemented. The ML/data-science side is ready for backend/frontend integration.

## Objective-wise status

| Objective | Status | Completed | Remaining |
|---|---|---|---|
| A — Atypical Symptom Detection | 🟢 Core prototype | Emerging/recurring symptom modelling and cross-hospital symptom analysis | UI integration; advanced spatial-temporal/statistical methods remain future work |
| B — Epidemic/Pandemic Detection | 🟢 Core prototype | Weekly cases, growth rates, hospital alerts and cross-hospital outbreak assessment | UI integration; advanced national-scale spatial-temporal methods remain future work |
| C — Decentralized/Federated Healthcare AI | 🟢 Core prototype | 10 simulated hospitals, local TabNet, FedAvg, 3 rounds, privacy audit/minimization/pseudonymization/verification | Backend/UI integration; DP, secure aggregation, FedProx/FedNova, compression/versioning remain future work |
| D — Structured Local Clinical Database | 🟢 Foundation complete | PostgreSQL schema, encounter/symptom/treatment/complication tables, master/mapping tables | Backend API exposure, UI entry/view and production security/integration |
| E — AI Treatment Advisor | 🟢 Core prototype | Candidate mapping, Random Forest success model, ranking, recovery estimation, risk information and final advisor | Backend/UI integration; advanced epidemiology/formulary filtering, confidence intervals and explainability remain future work |

## ML completion

The ML side has been:
- organized into functional packages
- dependency-configured
- tested after reorganization
- successfully run through Flower
- validated with 10 simulated hospitals
- pushed to GitHub
- documented in `ML/ML_handoff.md`

## Federated-learning result

Configuration:
- 10 simulated hospitals
- TabNet
- FedAvg
- 3 rounds
- multi-label symptom prediction

Final global metrics:
- Accuracy: 87.82%
- Micro-F1: 39.23%
- Macro-F1: 5.83%
- Hamming Loss: 12.18%

Limitation:
Accuracy and Hamming loss improved across rounds, but Micro-F1 did not improve monotonically and Macro-F1 remained relatively low. Report this honestly.

## Treatment model result

Training:
- 14,165 treatment records
- encounter-level leakage-aware split
- zero encounter overlap

Validation:
- Accuracy: 0.8799
- ROC-AUC: 0.6317

The advisor is decision support, not autonomous medical prescribing.

## Privacy validation

Current checks:
- Pseudonym generation — PASS
- Pseudonym uniqueness — PASS
- Original identifier removal — PASS
- Deterministic local linkage — PASS

The privacy audit covers 46 columns.

## What remains immediately before Review 2

### Backend
- expose ML/database functionality through APIs
- implement service/interface layer
- connect database safely
- integrate treatment advisor
- integrate surveillance outputs
- expose FL status/results

### Frontend
Build:
- Dashboard
- Clinical / Patient
- Surveillance
- Federated Learning
- Treatment Advisor
- Privacy / Audit

### Joint
- end-to-end privacy enforcement audit
- complete application workflow
- integration testing
- final demonstration
- Review 2 slides/script
- verify no prohibited identifiers/raw data are exposed

## What is not left for the ML team

The ML implementation should be treated as frozen for the current Review 2 integration phase.

Do not:
- replace models unnecessarily
- redesign FL architecture
- add advanced algorithms only for presentation
- start new ML features unless an actual integration bug is found

Priority is integration and demonstration.

## Future scope

### Privacy/security
- Differential privacy
- Secure multiparty aggregation
- Production encryption
- Role-based access control
- Detailed audit logging

### Federated learning
- FedProx
- FedNova
- Gradient compression/quantization
- Asynchronous/partial participation
- Model versioning and rollback

### Advanced AI
- Transformer-based encoders
- Graph neural networks
- Time-series models
- SHAP/attention explainability
- Advanced anomaly detection
- Advanced epidemiological modelling

### Deployment
- HMIS integration
- Docker deployment
- Mobile/web data entry
- Offline inference
- Batch uploads
- Intermittent-connectivity support
- Large-scale deployment across many facilities

These are future scope, not current Review 2 deliverables.

## Recommended status statement

> The project has completed the core prototype implementation of atypical symptom analysis, hospital-level and cross-hospital surveillance, federated multi-label symptom learning across 10 simulated hospitals, a structured clinical database foundation, privacy-aware data processing, and AI-assisted treatment recommendation. The current phase is focused on backend/frontend integration, end-to-end privacy verification, final system testing and Review 2 demonstration. Advanced security, AI and production-deployment capabilities described in the broader architecture remain future enhancements.
