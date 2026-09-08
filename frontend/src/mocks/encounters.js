// Sample authorised-scope encounter records for the Doctor Portal history/detail
// views. Keyed by patient_token, never raw patient_id (spec section 13).

export const ENCOUNTERS = [
  {
    encounter_id: 'ENC-7B7DEBF90A',
    patient_token: 'pt_9f4c1a2b',
    hospital_id: 'H001',
    visit_timestamp: '2026-09-08T08:30:00Z',
    age: 54,
    gender: 'Female',
    disease_id: 'D003',
    disease_name: 'Dengue',
    severity_id: 'SV002',
    severity_label: 'Moderate',
    symptoms: ['Fever', 'Headache', 'Joint Pain', 'Rash', 'Retro-orbital Pain'],
    discharge_status: 'Stable',
  },
  {
    encounter_id: 'ENC-4C1A9930F2',
    patient_token: 'pt_2a7710de',
    hospital_id: 'H001',
    visit_timestamp: '2026-09-07T14:05:00Z',
    age: 33,
    gender: 'Male',
    disease_id: 'D001',
    disease_name: 'Influenza',
    severity_id: 'SV001',
    severity_label: 'Mild',
    symptoms: ['Fever', 'Muscle Pain', 'Fatigue', 'Sore Throat'],
    discharge_status: 'Recovered',
  },
  {
    encounter_id: 'ENC-9920AB77C1',
    patient_token: 'pt_bb31c0a4',
    hospital_id: 'H001',
    visit_timestamp: '2026-09-06T10:45:00Z',
    age: 68,
    gender: 'Male',
    disease_id: 'D007',
    disease_name: 'Pneumonia',
    severity_id: 'SV003',
    severity_label: 'Severe',
    symptoms: ['Breathlessness', 'Chest Pain', 'Persistent Cough', 'Fatigue', 'Chills'],
    discharge_status: 'Referred',
  },
  {
    encounter_id: 'ENC-1D5E4402B8',
    patient_token: 'pt_57e9f130',
    hospital_id: 'H002',
    visit_timestamp: '2026-09-06T09:10:00Z',
    age: 41,
    gender: 'Female',
    disease_id: 'D002',
    disease_name: 'COVID-19',
    severity_id: 'SV002',
    severity_label: 'Moderate',
    symptoms: ['Dry Cough', 'Loss of Smell', 'Loss of Taste', 'Fatigue', 'Headache'],
    discharge_status: 'Stable',
  },
]

export const DOCTOR_DASHBOARD = {
  hospital_id: 'H001',
  ward: 'Ward 4B — Cardiology',
  recent_encounters: ENCOUNTERS.filter((e) => e.hospital_id === 'H001').length,
  encounters_today: 1,
  local_alert: { disease_name: 'Dengue', alert_level: 'ORANGE', hospital_id: 'H004', note: 'Regional signal near your network.' },
  model_status: { advisor: 'READY', global_model_version: 'fl-global-r3', last_fl_run: '2026-09-06' },

  kpis: {
    active_patients: { value: 1284, delta: '3.2% vs last week', deltaTone: 'up', spark: [980, 1010, 1005, 1060, 1120, 1180, 1240, 1284] },
    critical_alerts: { value: 7, delta: '2 new since 6am', deltaTone: 'warn', spark: [3, 4, 2, 5, 4, 6, 5, 7] },
    avg_recovery_score: { value: 84.6, delta: '1.8 pts this month', deltaTone: 'warn', spark: [82.1, 82.4, 83.0, 82.8, 83.6, 84.0, 84.2, 84.6] },
    advisor_runs: { value: 42, delta: '9 today', deltaTone: 'up', spark: [18, 22, 20, 27, 25, 31, 36, 42] },
  },

  weekly_admissions: [
    { x: 'Mon', Emergency: 41, Scheduled: 32 },
    { x: 'Tue', Emergency: 49, Scheduled: 37 },
    { x: 'Wed', Emergency: 37, Scheduled: 27 },
    { x: 'Thu', Emergency: 52, Scheduled: 38 },
    { x: 'Fri', Emergency: 46, Scheduled: 35 },
  ],

  diagnosis_mix: [
    { name: 'Influenza', value: 322 },
    { name: 'COVID-19', value: 268 },
    { name: 'Dengue', value: 214 },
    { name: 'Pneumonia', value: 176 },
    { name: 'Typhoid', value: 141 },
    { name: 'Malaria', value: 98 },
    { name: 'Other', value: 65 },
  ],

  priority_queue: [
    { patient_token: 'pt_bb31c0a4', risk: 'HIGH', reason: 'Rising resp. rate + low SpO₂', disease_name: 'Pneumonia' },
    { patient_token: 'pt_9f4c1a2b', risk: 'MODERATE', reason: 'Platelet trend + dengue day 4', disease_name: 'Dengue' },
    { patient_token: 'pt_57e9f130', risk: 'MODERATE', reason: 'Persistent hypoxia on room air', disease_name: 'COVID-19' },
  ],
}
