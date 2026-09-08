// Fixed example of the E13 "final advisor output" contract (spec section 8).
//
// Used ONLY as a fallback when the FastAPI backend is unreachable, so the UI can
// be developed and demonstrated before Objective E16 exists. It is clearly
// labelled as sample data wherever it is shown. When the backend is built, the
// real Pydantic schema is the source of truth - align this fixture to it, do not
// let the fixture drive the contract.

import { diseaseName, severityLabel, hospitalName, SEVERITIES } from './master'

export const E13_SAMPLE = {
  advisor_version: 'E13.1',
  advisor_status: 'COMPLETED',
  encounter_id: 'ENC-7B7DEBF90A',
  generated_at: '2026-09-08T09:42:00Z',
  model_version: 'treatment_success_rf_v1',
  configuration_version: 'e4_config_2026_08',

  patient_context: {
    hospital_id: 'H004',
    hospital_name: 'Hospital H004',
    age: 54,
    gender: 'Female',
    disease_id: 'D003',
    disease_name: 'Dengue',
    severity_id: 'S2',
    severity_label: 'Moderate',
    symptoms: ['Fever', 'Headache', 'Joint Pain', 'Rash', 'Retro-orbital Pain', 'Nausea'],
    vitals: {
      temperature_c: 38.9,
      heart_rate: 104,
      respiratory_rate: 20,
      spo2: 96,
      systolic_bp: 108,
      diastolic_bp: 72,
    },
    comorbidity_flags: ['Hypertension'],
    pregnancy_flag: false,
  },

  regional_epidemiology: {
    available: true,
    region: 'Region covering Hospital H004',
    disease_name: 'Dengue',
    activity_level: 'ORANGE',
    trend: 'RISING',
    recent_case_count: 213,
    baseline_case_count: 90,
    as_of: '2026-09-07',
    note: 'Aggregated hospital-level surveillance signal (Objective B). Not patient-level data.',
  },

  summary: {
    candidate_count: 5,
    eligible_count: 4,
    excluded_count: 1,
    top_treatment_id: 'T002',
    top_treatment_name: 'IV fluid resuscitation + supportive care',
    overall_data_confidence: 'MODERATE',
  },

  recommendations: [
    {
      rank: 1,
      treatment_id: 'T002',
      treatment_name: 'IV fluid resuscitation + supportive care',
      final_score: 0.938,
      first_line: true,
      treatment_success: {
        calibrated_probability: 0.86,
        raw_probability: 0.83,
        basis: 'E6 RandomForest success model + E7 probability calibration',
      },
      uncertainty: {
        level: 'LOW',
        predictive_interval: [0.8, 0.91],
        note: 'Model-derived predictive spread (E8), not a formal statistical confidence interval.',
      },
      recovery: {
        expected_days: 5,
        interval_days: [4, 7],
        basis: 'E9 recovery estimation for disease + severity',
      },
      risk: {
        level: 'LOW',
        complication_flags: [],
        notes: 'No project-defined high-risk complication signals for this profile.',
      },
      clinical_configuration: {
        availability: 'AVAILABLE',
        guideline_status: 'PROJECT_SUPPORTED',
        resource_tier: 'LOW',
        safety_review_required: false,
      },
      explainability: {
        method: 'SHAP (E11)',
        disclaimer: 'Feature attributions are associational, not causal.',
        top_features: [
          { feature: 'severity_label', value: 'Moderate', direction: 'increases', contribution: 0.14 },
          { feature: 'disease_name', value: 'Dengue', direction: 'increases', contribution: 0.11 },
          { feature: 'age', value: 54, direction: 'decreases', contribution: -0.06 },
          { feature: 'heart_rate', value: 104, direction: 'decreases', contribution: -0.04 },
          { feature: 'symptom:Rash', value: 1, direction: 'increases', contribution: 0.03 },
        ],
      },
    },
    {
      rank: 2,
      treatment_id: 'T005',
      treatment_name: 'Oral rehydration + outpatient monitoring',
      final_score: 0.881,
      first_line: false,
      treatment_success: {
        calibrated_probability: 0.79,
        raw_probability: 0.77,
        basis: 'E6 RandomForest success model + E7 probability calibration',
      },
      uncertainty: {
        level: 'MODERATE',
        predictive_interval: [0.68, 0.87],
        note: 'Model-derived predictive spread (E8), not a formal statistical confidence interval.',
      },
      recovery: {
        expected_days: 6,
        interval_days: [4, 9],
        basis: 'E9 recovery estimation for disease + severity',
      },
      risk: {
        level: 'MODERATE',
        complication_flags: ['Progression to severe dengue if unmonitored'],
        notes: 'Project-defined risk elevated by age and hypertension comorbidity.',
      },
      clinical_configuration: {
        availability: 'AVAILABLE',
        guideline_status: 'PROJECT_SUPPORTED_REVIEW',
        resource_tier: 'LOW',
        safety_review_required: true,
      },
      explainability: {
        method: 'SHAP (E11)',
        disclaimer: 'Feature attributions are associational, not causal.',
        top_features: [
          { feature: 'severity_label', value: 'Moderate', direction: 'decreases', contribution: -0.09 },
          { feature: 'comorbidity:Hypertension', value: 1, direction: 'decreases', contribution: -0.07 },
          { feature: 'age', value: 54, direction: 'decreases', contribution: -0.05 },
          { feature: 'spo2', value: 96, direction: 'increases', contribution: 0.02 },
        ],
      },
    },
    {
      rank: 3,
      treatment_id: 'T011',
      treatment_name: 'Platelet transfusion protocol',
      final_score: 0.612,
      first_line: false,
      treatment_success: {
        calibrated_probability: 0.58,
        raw_probability: 0.61,
        basis: 'E6 RandomForest success model + E7 probability calibration',
      },
      uncertainty: {
        level: 'HIGH',
        predictive_interval: [0.39, 0.74],
        note: 'Model-derived predictive spread (E8), not a formal statistical confidence interval.',
      },
      recovery: {
        expected_days: 8,
        interval_days: [5, 13],
        basis: 'E9 recovery estimation for disease + severity',
      },
      risk: {
        level: 'HIGH',
        complication_flags: ['Transfusion reaction', 'Fluid overload with hypertension'],
        notes: 'Project-defined risk high; reserve for platelet count / bleeding criteria not met by this profile.',
      },
      clinical_configuration: {
        availability: 'LIMITED',
        guideline_status: 'NOT_SUPPORTED',
        resource_tier: 'HIGH',
        safety_review_required: true,
      },
      explainability: {
        method: 'SHAP (E11)',
        disclaimer: 'Feature attributions are associational, not causal.',
        top_features: [
          { feature: 'severity_label', value: 'Moderate', direction: 'decreases', contribution: -0.18 },
          { feature: 'resource_tier', value: 'HIGH', direction: 'decreases', contribution: -0.12 },
          { feature: 'guideline_status', value: 'NOT_SUPPORTED', direction: 'decreases', contribution: -0.1 },
        ],
      },
    },
    {
      rank: 4,
      treatment_id: 'T014',
      treatment_name: 'Broad-spectrum antibiotics',
      final_score: 0.401,
      first_line: false,
      treatment_success: {
        calibrated_probability: 0.34,
        raw_probability: 0.3,
        basis: 'E6 RandomForest success model + E7 probability calibration',
      },
      uncertainty: {
        level: 'MODERATE',
        predictive_interval: [0.24, 0.45],
        note: 'Model-derived predictive spread (E8), not a formal statistical confidence interval.',
      },
      recovery: {
        expected_days: 7,
        interval_days: [5, 11],
        basis: 'E9 recovery estimation for disease + severity',
      },
      risk: {
        level: 'MODERATE',
        complication_flags: ['Antibiotic exposure without bacterial indication'],
        notes: 'Included for completeness; low modelled success for a viral presentation.',
      },
      clinical_configuration: {
        availability: 'AVAILABLE',
        guideline_status: 'NOT_SUPPORTED',
        resource_tier: 'MEDIUM',
        safety_review_required: false,
      },
      explainability: {
        method: 'SHAP (E11)',
        disclaimer: 'Feature attributions are associational, not causal.',
        top_features: [
          { feature: 'disease_name', value: 'Dengue', direction: 'decreases', contribution: -0.22 },
          { feature: 'guideline_status', value: 'NOT_SUPPORTED', direction: 'decreases', contribution: -0.09 },
        ],
      },
    },
  ],

  excluded_treatments: [
    {
      treatment_id: 'T009',
      treatment_name: 'High-dose NSAID protocol',
      stage: 'E3',
      reason:
        'E3 clinical eligibility: NSAIDs contraindicated in suspected dengue (bleeding risk). Removed before ranking.',
    },
  ],

  ranking_method: 'E12 project-defined weighted scoring (not a clinically validated ranking)',
  ranking_weights: {
    success: 0.4,
    uncertainty: 0.15,
    recovery: 0.15,
    risk: 0.15,
    availability: 0.05,
    guideline: 0.05,
    resource: 0.05,
  },

  disclaimer:
    'This treatment advisor provides decision support only. It is not an autonomous prescription, ' +
    'not a causal treatment-effect estimate, and not a clinical guideline. Rankings use project-defined ' +
    'weights and are not clinically validated. Uncertainty and recovery intervals are model-derived ' +
    'predictive spreads, not formal statistical confidence intervals. A qualified clinician is ' +
    'responsible for the final treatment decision.',
}

// ---------------------------------------------------------------------------
// Deterministic sample E13 builder for the "submit a context" flow.
// Not a model - just makes the demo respond to inputs (spec section 14, step 6)
// so severity / SpO2 / age visibly move the numbers. Clearly labelled as sample.
// ---------------------------------------------------------------------------

function clamp(x, lo, hi) {
  return Math.max(lo, Math.min(hi, x))
}

const SEVERITY_FACTOR = { SV001: 0.06, SV002: 0, SV003: -0.14 }
const LEVEL_FROM_SCORE = (s) => (s >= 0.66 ? 'LOW' : s >= 0.4 ? 'MODERATE' : 'HIGH')

export function buildAdvisorFromContext(ctx = {}) {
  const severityId = ctx.severity_id || 'SV002'
  const age = Number(ctx.age) || 40
  const spo2 = Number(ctx.spo2) || 97
  const symptoms = Array.isArray(ctx.symptoms) ? ctx.symptoms : []

  const sevAdj = SEVERITY_FACTOR[severityId] ?? 0
  const ageAdj = age >= 60 ? -0.08 : age >= 45 ? -0.04 : 0
  const spo2Adj = spo2 < 92 ? -0.12 : spo2 < 95 ? -0.05 : 0
  const base = 0.8 + sevAdj + ageAdj + spo2Adj

  const catalogue = [
    { treatment_id: 'T002', treatment_name: 'IV fluid resuscitation + supportive care', first_line: true, bias: 0.06, tier: 'LOW', guide: 'PROJECT_SUPPORTED', avail: 'AVAILABLE' },
    { treatment_id: 'T005', treatment_name: 'Oral rehydration + outpatient monitoring', first_line: false, bias: -0.02, tier: 'LOW', guide: 'PROJECT_SUPPORTED_REVIEW', avail: 'AVAILABLE' },
    { treatment_id: 'T014', treatment_name: 'Broad-spectrum antibiotics', first_line: false, bias: -0.22, tier: 'MEDIUM', guide: 'NOT_SUPPORTED', avail: 'AVAILABLE' },
    { treatment_id: 'T011', treatment_name: 'Inpatient protocol with specialist review', first_line: false, bias: -0.3, tier: 'HIGH', guide: 'NOT_SUPPORTED', avail: 'LIMITED' },
  ]

  const recommendations = catalogue
    .map((t) => {
      const p = clamp(base + t.bias, 0.05, 0.97)
      const width = clamp(0.06 + (1 - p) * 0.28, 0.05, 0.4)
      const uLevel = LEVEL_FROM_SCORE(1 - width)
      const riskScore = clamp(p - (t.tier === 'HIGH' ? 0.2 : t.tier === 'MEDIUM' ? 0.08 : 0), 0.05, 0.97)
      const rLevel = LEVEL_FROM_SCORE(riskScore)
      const recDays = Math.round(clamp(5 + (1 - p) * 10 + (severityId === 'SV003' ? 3 : 0), 3, 21))
      const finalScore = clamp(
        0.4 * p + 0.15 * (1 - width) + 0.15 * (1 - recDays / 21) + 0.15 * riskScore +
          0.05 * (t.avail === 'AVAILABLE' ? 1 : t.avail === 'LIMITED' ? 0.5 : 0) +
          0.05 * (t.guide === 'PROJECT_SUPPORTED' ? 1 : t.guide === 'PROJECT_SUPPORTED_REVIEW' ? 0.5 : 0) +
          0.05 * (t.tier === 'LOW' ? 1 : t.tier === 'MEDIUM' ? 0.6 : 0.2),
        0,
        1
      )
      return {
        treatment_id: t.treatment_id,
        treatment_name: t.treatment_name,
        first_line: t.first_line,
        final_score: Number(finalScore.toFixed(3)),
        treatment_success: {
          calibrated_probability: Number(p.toFixed(2)),
          raw_probability: Number(clamp(p - 0.03, 0.03, 0.97).toFixed(2)),
          basis: 'E6 RandomForest success model + E7 probability calibration',
        },
        uncertainty: {
          level: uLevel,
          predictive_interval: [Number(clamp(p - width / 2, 0.02, 0.98).toFixed(2)), Number(clamp(p + width / 2, 0.02, 0.99).toFixed(2))],
          note: 'Model-derived predictive spread (E8), not a formal statistical confidence interval.',
        },
        recovery: {
          expected_days: recDays,
          interval_days: [Math.max(2, recDays - 2), recDays + 4],
          basis: 'E9 recovery estimation for disease + severity',
        },
        risk: {
          level: rLevel,
          complication_flags:
            rLevel === 'HIGH'
              ? ['Project-defined risk elevated by resource tier and patient profile']
              : rLevel === 'MODERATE'
              ? ['Monitor for progression given age / severity']
              : [],
          notes: 'Project-defined rule-based indicators (E10).',
        },
        clinical_configuration: {
          availability: t.avail,
          guideline_status: t.guide,
          resource_tier: t.tier,
          safety_review_required: t.guide === 'NOT_SUPPORTED' || rLevel === 'HIGH',
        },
        explainability: {
          method: 'SHAP (E11)',
          disclaimer: 'Feature attributions are associational, not causal.',
          top_features: [
            { feature: 'severity_label', value: severityLabel(severityId), direction: sevAdj >= 0 ? 'increases' : 'decreases', contribution: Number((sevAdj || 0.02).toFixed(2)) },
            { feature: 'spo2', value: spo2, direction: spo2Adj < 0 ? 'decreases' : 'increases', contribution: Number((spo2Adj || 0.01).toFixed(2)) },
            { feature: 'age', value: age, direction: ageAdj < 0 ? 'decreases' : 'increases', contribution: Number((ageAdj || 0.01).toFixed(2)) },
            { feature: 'symptom_count', value: symptoms.length, direction: 'increases', contribution: 0.02 },
          ],
        },
      }
    })
    .sort((a, b) => b.final_score - a.final_score)
    .map((r, i) => ({ ...r, rank: i + 1 }))

  return {
    ...E13_SAMPLE,
    encounter_id: ctx.encounter_id || `ENC-DEMO-${severityId}`,
    generated_at: new Date().toISOString(),
    advisor_status: 'COMPLETED',
    patient_context: {
      hospital_id: ctx.hospital_id || 'H001',
      hospital_name: hospitalName(ctx.hospital_id || 'H001'),
      age,
      gender: ctx.gender || 'Unknown',
      disease_id: ctx.disease_id || 'D003',
      disease_name: diseaseName(ctx.disease_id || 'D003'),
      severity_id: severityId,
      severity_label: severityLabel(severityId),
      symptoms,
      vitals: {
        temperature_c: Number(ctx.temperature) || null,
        heart_rate: Number(ctx.heart_rate) || null,
        respiratory_rate: Number(ctx.respiratory_rate) || null,
        spo2,
        systolic_bp: Number(ctx.systolic_bp) || null,
        diastolic_bp: Number(ctx.diastolic_bp) || null,
      },
      comorbidity_flags: [],
      pregnancy_flag: false,
    },
    summary: {
      candidate_count: recommendations.length + 1,
      eligible_count: recommendations.length,
      excluded_count: 1,
      top_treatment_id: recommendations[0]?.treatment_id ?? null,
      top_treatment_name: recommendations[0]?.treatment_name ?? null,
      overall_data_confidence: recommendations[0]?.uncertainty.level === 'LOW' ? 'MODERATE' : 'LOW',
    },
    recommendations,
    _mock: true,
  }
}

export const SEVERITY_OPTIONS = SEVERITIES

export const E13_SAMPLE_NO_CANDIDATES = {
  ...E13_SAMPLE,
  encounter_id: 'ENC-NOCAND01',
  advisor_status: 'NO_CANDIDATES',
  summary: {
    candidate_count: 0,
    eligible_count: 0,
    excluded_count: 0,
    top_treatment_id: null,
    top_treatment_name: null,
    overall_data_confidence: 'NOT_AVAILABLE',
  },
  recommendations: [],
  excluded_treatments: [],
}
