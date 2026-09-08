// Shape documentation for the backend contract (spec sections 7 & 8).
// JSDoc only - there is no TypeScript build. These typedefs describe what the
// FastAPI layer is expected to return so pages and mocks stay aligned.

/**
 * @typedef {'DOCTOR'|'HOSPITAL_ADMIN'|'PUBLIC_HEALTH_ADMIN'|'TECH_REVIEWER'} Role
 */

/**
 * @typedef {Object} PatientContext  // E1
 * @property {string} hospital_id
 * @property {string} [hospital_name]
 * @property {number} age
 * @property {string} gender
 * @property {string} disease_id
 * @property {string} [disease_name]
 * @property {string} severity_id
 * @property {string} [severity_label]
 * @property {string[]} symptoms
 * @property {Object} vitals
 * @property {string[]} [comorbidity_flags]
 * @property {boolean} [pregnancy_flag]
 */

/**
 * @typedef {Object} Recommendation  // one entry of E13.recommendations
 * @property {number} rank
 * @property {string} treatment_id
 * @property {string} treatment_name
 * @property {number} final_score               // E12 weighted score (0..1)
 * @property {boolean} [first_line]
 * @property {{calibrated_probability:number, raw_probability:number, basis:string}} treatment_success  // E6+E7
 * @property {{level:'LOW'|'MODERATE'|'HIGH', predictive_interval:[number,number], note:string}} uncertainty  // E8
 * @property {{expected_days:number, interval_days:[number,number], basis:string}} recovery  // E9
 * @property {{level:'LOW'|'MODERATE'|'HIGH', complication_flags:string[], notes:string}} risk  // E10
 * @property {{availability:string, guideline_status:string, resource_tier:string, safety_review_required:boolean}} clinical_configuration  // E4
 * @property {{method:string, disclaimer:string, top_features:Array<{feature:string,value:*,direction:string,contribution:number}>}} explainability  // E11
 */

/**
 * @typedef {Object} AdvisorOutput  // E13
 * @property {string} advisor_version
 * @property {'COMPLETED'|'NO_CANDIDATES'|'PARTIAL'} advisor_status
 * @property {string} encounter_id
 * @property {string} [generated_at]
 * @property {string} [model_version]
 * @property {string} [configuration_version]
 * @property {PatientContext} patient_context
 * @property {Object} regional_epidemiology   // E5; { available:boolean, ... }
 * @property {Object} summary
 * @property {Recommendation[]} recommendations
 * @property {Array<{treatment_id:string,treatment_name:string,stage:string,reason:string}>} excluded_treatments
 * @property {string} ranking_method
 * @property {Object} ranking_weights
 * @property {string} disclaimer
 */

export {}
