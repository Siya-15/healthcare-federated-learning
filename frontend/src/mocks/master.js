// Controlled clinical vocabularies used to populate form options and labels
// (spec section 4: loader.py + master/mapping data). In sample mode these stand
// in for GET /api/clinical/form-options.

export const HOSPITALS = Array.from({ length: 10 }, (_, i) => {
  const id = `H${String(i + 1).padStart(3, '0')}`
  return { hospital_id: id, hospital_name: `Hospital ${id}` }
})

export const DISEASES = [
  { disease_id: 'D001', disease_name: 'Influenza' },
  { disease_id: 'D002', disease_name: 'COVID-19' },
  { disease_id: 'D003', disease_name: 'Dengue' },
  { disease_id: 'D004', disease_name: 'Typhoid' },
  { disease_id: 'D005', disease_name: 'Malaria' },
  { disease_id: 'D006', disease_name: 'Tuberculosis' },
  { disease_id: 'D007', disease_name: 'Pneumonia' },
  { disease_id: 'D008', disease_name: 'Acute Bronchitis' },
]

export const SEVERITIES = [
  { severity_id: 'SV001', severity_label: 'Mild' },
  { severity_id: 'SV002', severity_label: 'Moderate' },
  { severity_id: 'SV003', severity_label: 'Severe' },
]

// The 27 symptom labels used across E1/E6 and the emerging-symptom modules.
export const SYMPTOMS = [
  'Abdominal Pain',
  'Anaemia',
  'Bleeding',
  'Breathlessness',
  'Chest Pain',
  'Chills',
  'Dehydration',
  'Diarrhoea',
  'Dry Cough',
  'Fatigue',
  'Fever',
  'Headache',
  'Joint Pain',
  'Loss of Appetite',
  'Loss of Smell',
  'Loss of Taste',
  'Muscle Pain',
  'Nausea',
  'Night Sweats',
  'Persistent Cough',
  'Rash',
  'Retro-orbital Pain',
  'Runny Nose',
  'Sore Throat',
  'Sweating',
  'Vomiting',
  'Weight Loss',
]

export const FORM_OPTIONS = {
  hospitals: HOSPITALS,
  diseases: DISEASES,
  severities: SEVERITIES,
  symptoms: SYMPTOMS,
}

export function diseaseName(id) {
  return DISEASES.find((d) => d.disease_id === id)?.disease_name || id
}
export function severityLabel(id) {
  return SEVERITIES.find((s) => s.severity_id === id)?.severity_label || id
}
export function hospitalName(id) {
  return HOSPITALS.find((h) => h.hospital_id === id)?.hospital_name || id
}
