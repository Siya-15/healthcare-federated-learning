// Sample privacy / governance outputs (Objective C). What the audited prototype
// actually supports is marked IMPLEMENTED; conceptual-only mechanisms are marked
// NOT_IMPLEMENTED and must not be shown as active (spec sections 11 & 16).

export const PRIVACY_POLICY = {
  updated_at: '2026-09-05',
  controls: [
    { control: 'Data minimization (field-level policy)', status: 'IMPLEMENTED', detail: 'Only configured fields leave the local processing step.' },
    { control: 'Privacy classification of DB columns', status: 'IMPLEMENTED', detail: 'Each column tagged (identifier / clinical / derived / safe).' },
    { control: 'Pseudonymization (patient_token)', status: 'IMPLEMENTED', detail: 'Deterministic SHA-256(secret + ":" + id); raw patient_id never surfaced.' },
    { control: 'Pseudonymization verification', status: 'IMPLEMENTED', detail: 'Automated check that application views carry no raw identifiers.' },
    { control: 'Federated learning (data stays local)', status: 'IMPLEMENTED', detail: 'Only model parameters are exchanged; CSV rows never leave the client.' },
    { control: 'Differential privacy', status: 'NOT_IMPLEMENTED', detail: 'Conceptual architecture only. Not active.' },
    { control: 'Secure aggregation', status: 'NOT_IMPLEMENTED', detail: 'Conceptual architecture only. Not active.' },
    { control: 'Update encryption in transit (explicit)', status: 'NOT_IMPLEMENTED', detail: 'Not demonstrated in the prototype.' },
  ],
}

export const PRIVACY_DATA_FLOW = {
  steps: [
    { step: 'Local clinical data', scope: 'Hospital only', detail: 'PostgreSQL: encounters, symptoms, vitals, treatments, labs, imaging.' },
    { step: 'Local processing / training', scope: 'Hospital only', detail: 'E1–E12 advisor and Flower client training run against local data.' },
    { step: 'Model update', scope: 'Leaves hospital', detail: 'TabNet parameter tensors only — no patient rows, no identifiers.' },
    { step: 'Central aggregation', scope: 'Coordinator', detail: 'FedAvg over submitted parameters (Flower server).' },
    { step: 'Global model', scope: 'Shared back', detail: 'Aggregated weights redistributed to hospitals.' },
  ],
  guarantee_note:
    'Raw patient data never leaves the hospital in this prototype. Only model-update information is exchanged. Stronger cryptographic guarantees (DP, secure aggregation) are not implemented.',
}

export const PRIVACY_AUDIT = {
  ran_at: '2026-09-05T09:00:00Z',
  checks: [
    { check: 'No raw patient_id in application responses', result: 'PASS' },
    { check: 'No raw encounter_id surfaced outside clinical scope', result: 'PASS' },
    { check: 'Surveillance outputs are aggregate-only', result: 'PASS' },
    { check: 'Federated payloads contain parameters only', result: 'PASS' },
    { check: 'Pseudonym reversibility test (should fail to reverse)', result: 'PASS' },
    { check: 'Differential-privacy noise present', result: 'NOT_IMPLEMENTED' },
  ],
  minimization_matrix: [
    { field: 'patient_id', local_db: true, local_processing: true, transmitted: false, aggregate_view: false },
    { field: 'patient_token', local_db: true, local_processing: true, transmitted: false, aggregate_view: true },
    { field: 'age', local_db: true, local_processing: true, transmitted: false, aggregate_view: true },
    { field: 'symptoms (27)', local_db: true, local_processing: true, transmitted: false, aggregate_view: true },
    { field: 'vitals', local_db: true, local_processing: true, transmitted: false, aggregate_view: false },
    { field: 'model parameters', local_db: false, local_processing: true, transmitted: true, aggregate_view: false },
  ],
}
