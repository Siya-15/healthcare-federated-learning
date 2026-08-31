# Healthcare Project — Project Overview

## What the project is

The project is a privacy-aware, federated-learning-powered healthcare platform intended for public healthcare facilities in India.

The architecture uses local clinical databases at individual facilities. Patient-level information remains at the facility, while collaborative machine learning is performed through federated learning rather than centralizing raw patient records.

The platform is designed around three primary capabilities:
1. Detect new or atypical disease symptoms.
2. Detect potential epidemic/pandemic events early.
3. Provide evidence-based treatment decision support.

It also includes a standardized local clinical database and privacy-preserving mechanisms.

## Project objectives

### Objective A — Atypical Symptom Detection
Build a continuously refined AI capability that can identify new or atypical disease symptoms that diverge from established symptom profiles.

### Objective B — Epidemic/Pandemic Detection
Identify impending epidemic or pandemic events by analysing symptom trends, anomalous clusters and changes in incidence across healthcare facilities.

### Objective C — Decentralized/Federated Healthcare AI
Enable collaborative AI development across healthcare facilities without centralizing sensitive patient-level data. Federated learning is used so local data stays at participating facilities while model information is exchanged for aggregation.

### Objective D — Structured Local Clinical Database
Create a standardized local clinical database for symptoms, treatments, outcomes and treatment-success measurements.

### Objective E — AI Treatment Advisor
Provide clinicians with ranked treatment options based on patient information and available clinical knowledge, together with treatment-success probability, expected recovery time and risk information.

## Current Review 2 prototype

The current student prototype uses synthetic healthcare data and implements the core computational functionality for the objectives.

Implemented components include:
- Atypical/emerging symptom pattern analysis
- Hospital-level and cross-hospital surveillance
- Outbreak alerts
- Federated multi-label symptom learning
- Structured PostgreSQL clinical data
- Privacy audit, minimization, pseudonymization and verification
- Treatment-success prediction and treatment recommendation

## Technology

### Machine learning
- Python
- pandas
- NumPy
- scikit-learn
- PyTorch
- PyTorch TabNet
- Random Forest

### Federated learning
- Flower
- FedAvg
- Ray simulation backend
- 10 simulated hospitals
- 3 FL rounds

### Database
- PostgreSQL
- SQLAlchemy
- psycopg2

## Core architecture

```text
Hospital / PHC
     |
     +--> Local Clinical Database
     |
     +--> Local ML processing
     |
     +--> Local symptom / treatment analysis
     |
     +--> Federated model update
                  |
                  v
           Federated Server
                  |
                FedAvg
                  |
                  v
          Global model/update
                  |
                  v
       Participating facilities

Database / ML
      |
      v
   Backend API
      |
      v
   Frontend
```

The frontend must communicate through the backend. It should not directly access PostgreSQL or Python ML modules.

## Privacy boundary

The current FL workflow keeps raw patient-level records on the simulated hospital side. Model information is exchanged for federated aggregation.

The broader proposal additionally describes differential privacy, encryption and secure aggregation. These should be treated as future/extended capabilities unless separately implemented and validated.

## Prototype vs production

This repository is a working student prototype, not a production healthcare deployment.

Do not claim that these are already implemented:
- national-scale deployment across thousands of facilities
- differential privacy in FL aggregation
- secure multiparty aggregation
- production encryption/RBAC
- HMIS integration
- mobile/offline production deployment
- transformer/GNN/time-series architecture
- SHAP/attention explainability
- FedProx/FedNova
- model versioning/rollback

Those belong to future scope.
