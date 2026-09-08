// Sample federated-learning metadata (Objective C). Metadata only - raw update
// arrays and datasets are never exposed to the UI (spec sections 11, 13, 16).
// Honest metrics per CLAUDE.md / ML_handoff.md.

export const FEDERATED_NETWORK = {
  framework: 'Flower (flwr) — FedAvg',
  model: 'TabNet multi-label classifier (27 symptom labels)',
  total_hospitals: 10,
  participating_hospitals: 10,
  current_round: 3,
  total_rounds: 3,
  global_model_version: 'fl-global-r3',
  last_run: '2026-09-06T18:20:00Z',
  aggregation_status: 'COMPLETE',
  hospitals: Array.from({ length: 10 }, (_, i) => {
    const id = `H${String(i + 1).padStart(3, '0')}`
    return {
      hospital_id: id,
      local_training: 'COMPLETE',
      update_submitted: true,
      update_approved: true,
      local_epochs: 10,
      examples: 700 + i * 37,
    }
  }),
}

export const FEDERATED_ROUNDS = [
  {
    round: 1,
    participating_nodes: 10,
    aggregation: 'FedAvg',
    status: 'COMPLETE',
    started_at: '2026-09-06T17:40:00Z',
    metrics: { accuracy: 0.8455, micro_f1: 0.3712, macro_f1: 0.049, hamming_loss: 0.1402 },
  },
  {
    round: 2,
    participating_nodes: 10,
    aggregation: 'FedAvg',
    status: 'COMPLETE',
    started_at: '2026-09-06T18:00:00Z',
    metrics: { accuracy: 0.8719, micro_f1: 0.3689, macro_f1: 0.0551, hamming_loss: 0.1281 },
  },
  {
    round: 3,
    participating_nodes: 10,
    aggregation: 'FedAvg',
    status: 'COMPLETE',
    started_at: '2026-09-06T18:20:00Z',
    metrics: { accuracy: 0.8782, micro_f1: 0.3923, macro_f1: 0.0583, hamming_loss: 0.1218 },
  },
]

export const FEDERATED_MODEL = {
  global_model_version: 'fl-global-r3',
  training_round: 3,
  trained_at: '2026-09-06T18:20:00Z',
  status: 'VALIDATED',
  aggregation: 'FedAvg',
  clients: 10,
  server_rounds: 3,
  honest_metrics: { accuracy: 0.8782, micro_f1: 0.3923, macro_f1: 0.0583, hamming_loss: 0.1218 },
  caveats: [
    'Macro-F1 is low (0.0583) — minority symptom labels are largely not learned.',
    'Micro-F1 did not improve monotonically across rounds.',
    'Differential privacy and secure aggregation are NOT implemented.',
  ],
}
