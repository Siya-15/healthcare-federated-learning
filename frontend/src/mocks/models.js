// Sample AI-operations / transparency metadata (spec section 12). Metrics that
// the prototype does not compute are marked NOT_IMPLEMENTED.

export const MODEL_OVERVIEW = {
  pipeline: [
    { stage: 'E1', name: 'Patient context', kind: 'data' },
    { stage: 'E2', name: 'Candidate treatments', kind: 'rules' },
    { stage: 'E3', name: 'Clinical eligibility', kind: 'rules' },
    { stage: 'E4', name: 'Configuration enrichment', kind: 'config' },
    { stage: 'E5', name: 'Regional epidemiology', kind: 'context' },
    { stage: 'E6', name: 'Treatment-success model', kind: 'model' },
    { stage: 'E7', name: 'Probability calibration', kind: 'model' },
    { stage: 'E8', name: 'Uncertainty estimation', kind: 'model' },
    { stage: 'E9', name: 'Recovery estimation', kind: 'model' },
    { stage: 'E10', name: 'Risk & complications', kind: 'rules' },
    { stage: 'E11', name: 'SHAP explainability', kind: 'explain' },
    { stage: 'E12', name: 'Weighted ranking', kind: 'rank' },
  ],
  ranking_weights: {
    success: 0.4,
    uncertainty: 0.15,
    recovery: 0.15,
    risk: 0.15,
    availability: 0.05,
    guideline: 0.05,
    resource: 0.05,
  },
  note: 'E12 ranking weights are project-defined and transparent, not clinically validated.',
}

export const MODEL_METRICS = {
  treatment_advisor: [
    { model: 'E6 treatment success (RandomForest)', metric: 'Accuracy', value: '0.81' },
    { model: 'E6 treatment success (RandomForest)', metric: 'ROC-AUC', value: '0.84' },
    { model: 'E7 calibration', metric: 'Brier score', value: '0.146' },
    { model: 'E8 uncertainty', metric: 'Interval', value: '10th–90th percentile (tree spread)' },
    { model: 'E9 recovery time', metric: 'MAE (days)', value: '1.9' },
    { model: 'E9 recovery time', metric: 'R²', value: '0.62' },
  ],
  federated: [
    { model: 'FL global (round 3)', metric: 'Accuracy', value: '0.8782' },
    { model: 'FL global (round 3)', metric: 'Micro-F1', value: '0.3923' },
    { model: 'FL global (round 3)', metric: 'Macro-F1', value: '0.0583' },
    { model: 'FL global (round 3)', metric: 'Hamming loss', value: '0.1218' },
  ],
  not_implemented: ['Fairness / subgroup metrics', 'Calibration drift monitoring', 'Prospective clinical evaluation'],
}

export const MODEL_VERSIONS = [
  { component: 'E6 treatment_success_model.pkl', version: 'rf_v1', trained: '2026-08-29', status: 'ACTIVE' },
  { component: 'E7 calibration artifact', version: 'sigmoid_v1', trained: '2026-08-30', status: 'ACTIVE' },
  { component: 'E9 recovery_time_model.pkl', version: 'rf_v1', trained: '2026-08-31', status: 'ACTIVE' },
  { component: 'FL global model', version: 'fl-global-r3', trained: '2026-09-06', status: 'ACTIVE' },
  { component: 'FL global model', version: 'fl-global-r2', trained: '2026-09-06', status: 'SUPERSEDED' },
]
