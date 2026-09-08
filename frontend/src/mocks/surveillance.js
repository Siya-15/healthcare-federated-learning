// Sample surveillance outputs (Objectives A + B). Aggregate only - no patient
// rows (spec sections 10 & 13). Language stays within the audited prototype
// scope: weekly hospital surveillance and anomalous symptom patterns, NOT
// pathogen identification or epidemic forecasting.

const WEEKS = ['2026-W28', '2026-W29', '2026-W30', '2026-W31', '2026-W32', '2026-W33']

export const SURVEILLANCE_OVERVIEW = {
  monitored_hospitals: 10,
  current_alert_level: 'ORANGE',
  active_signals: 4,
  surveillance_period: `${WEEKS[0]} → ${WEEKS[WEEKS.length - 1]}`,
  updated_at: '2026-09-07',
  scope_note:
    'Weekly hospital-level surveillance and anomalous symptom-pattern detection (audited prototype). Not clinically validated pathogen or outbreak confirmation.',
  headline_signals: [
    { hospital_id: 'H004', disease_name: 'Dengue', alert_level: 'ORANGE', driver: 'Case growth + symptom-cluster persistence' },
    { hospital_id: 'H007', disease_name: 'Influenza', alert_level: 'YELLOW', driver: 'Above-baseline weekly count' },
    { hospital_id: 'H002', disease_name: 'COVID-19', alert_level: 'YELLOW', driver: 'Rising respiratory-symptom cluster' },
    { hospital_id: 'H009', disease_name: 'Typhoid', alert_level: 'GREEN', driver: 'Within expected range' },
  ],
}

export const SURVEILLANCE_ALERTS = [
  {
    id: 'ALRT-0041',
    hospital_id: 'H004',
    disease_name: 'Dengue',
    alert_level: 'ORANGE',
    score: 0.71,
    week: '2026-W33',
    drivers: ['Weekly count 2.4x baseline', 'Symptom cluster persisted 3 weeks', 'Cross-hospital corroboration (H003)'],
    recommended_action: 'Escalated surveillance; verify vector-control status; review admissions capacity.',
    persistence_weeks: 3,
    spatial_note: 'Signal also present at a neighbouring hospital (H003).',
  },
  {
    id: 'ALRT-0042',
    hospital_id: 'H007',
    disease_name: 'Influenza',
    alert_level: 'YELLOW',
    score: 0.44,
    week: '2026-W33',
    drivers: ['Weekly count 1.5x baseline', 'Fever + Muscle Pain + Fatigue cluster'],
    recommended_action: 'Continue monitoring; no escalation yet.',
    persistence_weeks: 1,
    spatial_note: 'Isolated to H007 this week.',
  },
  {
    id: 'ALRT-0043',
    hospital_id: 'H002',
    disease_name: 'COVID-19',
    alert_level: 'YELLOW',
    score: 0.39,
    week: '2026-W33',
    drivers: ['Rising Breathlessness + Persistent Cough cluster', 'Count near baseline but accelerating'],
    recommended_action: 'Monitor acceleration; recheck next week.',
    persistence_weeks: 2,
    spatial_note: 'Isolated to H002.',
  },
]

export const EMERGING_SYMPTOMS = {
  scope_note:
    'Objective A detects unusual / recurring symptom combinations relative to a rolling baseline. It does NOT infer a new pathogen or variant.',
  patterns: [
    { pattern: 'Fever + Rash + Retro-orbital Pain + Joint Pain', hospital_count: 3, frequency: 58, emergence_score: 0.68, status: 'WATCH', first_seen: '2026-W31' },
    { pattern: 'Breathlessness + Persistent Cough + Fatigue', hospital_count: 2, frequency: 41, emergence_score: 0.52, status: 'WATCH', first_seen: '2026-W32' },
    { pattern: 'Diarrhoea + Vomiting + Dehydration + Abdominal Pain', hospital_count: 4, frequency: 73, emergence_score: 0.47, status: 'MONITOR', first_seen: '2026-W30' },
    { pattern: 'Loss of Smell + Loss of Taste + Headache', hospital_count: 1, frequency: 12, emergence_score: 0.21, status: 'MONITOR', first_seen: '2026-W33' },
  ],
}

export const SURVEILLANCE_TRENDS = {
  weeks: WEEKS,
  series: [
    { disease_name: 'Dengue', observed: [34, 41, 52, 63, 88, 120], baseline: [40, 40, 42, 44, 45, 45] },
    { disease_name: 'Influenza', observed: [61, 58, 64, 70, 77, 92], baseline: [60, 60, 61, 62, 62, 63] },
    { disease_name: 'COVID-19', observed: [22, 20, 25, 28, 33, 39], baseline: [24, 24, 24, 25, 25, 25] },
  ],
  growth_note: 'Growth = observed vs rolling baseline. Prototype signal, not a forecast.',
}
