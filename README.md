# BauData Behavioral Segmentation & B2B Usage Analytics

This project analyzes BauData platform usage data to identify behavioral user profiles and translate them into actionable B2B commercial decisions.

The repository originally documented an academic/product strategy case. The current version focuses on the operational analytics layer: product usage, user behavior, company-level prioritization, and Power BI reporting for commercial decision-making.

## Business Goal

BauData is a B2B platform, so the most useful decision unit is not only the individual user but also the company account.

This project answers three practical questions:

- Which active companies are using BauData?
- Which companies have active users but no detected usage?
- Which companies and users should be activated, recovered, monitored, maintained, or expanded?

## Analytical Workflow

```text
PostHog events and sessions
        |
        v
Historical local extraction
        |
        v
Session and user feature engineering
        |
        v
K-Means clustering and model comparison
        |
        v
User-level commercial scoring
        |
        v
Company-level B2B summary
        |
        v
Power BI dashboard
```

## Main Components

- `scripts/posthog_historico_local.py`: downloads historical PostHog events and sessions using environment variables.
- `scripts/modeloml_baudata_local.py`: processes sessions and generates K-Means clustering outputs.
- `scripts/comparar_modelos_clustering.py`: compares clustering alternatives to support the modeling decision.
- `scripts/crear_analisis_empresas.py`: joins usage data with the company/user master file and creates the B2B layer for Power BI.
- `scripts/actualizar_baudata.ps1`: runs the local refresh pipeline.
- `Actualizar_BauData.cmd`: Windows launcher for the refresh pipeline.

## Dashboard Structure

The final Power BI report is designed around two business-facing pages:

- `Resumen Ejecutivo Empresas`: executive account view focused on company activation, active usage, non-usage, downloads, and commercial priority.
- `Accion Comercial Usuarios`: user-level action view focused on specific users, behavioral profile, recommended action, usage scores, and adoption signals.

The clustering layer is used as methodological support. It helps explain behavior, but the final dashboard story is commercial and operational.

## Data Privacy

This repository intentionally excludes raw data, company master files, Power BI files with embedded data, logs, generated outputs, and credentials.

The following should remain local/private:

- PostHog raw exports.
- Power BI `.pbix` files with real data.
- Excel/CSV files containing user e-mails or company/customer lists.
- API keys and legacy extraction scripts with hardcoded credentials.
- Generated outputs with sensitive company or user-level information.

To run the extraction locally, configure credentials with environment variables:

```powershell
$env:POSTHOG_PROJECT_ID="your_project_id"
$env:POSTHOG_API_KEY="your_posthog_api_key"
```

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Refresh Pipeline

From the project root:

```powershell
.\Actualizar_BauData.cmd
```

Or directly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\actualizar_baudata.ps1
```

After the local pipeline finishes, refresh Power BI manually from `Inicio > Actualizar`.

## Methodological Notes

The clustering model converts behavioral telemetry into interpretable user profiles. These profiles are combined with business rules such as active status, detected usage, download behavior, and interaction volume.

In this version, download activity is treated as a proxy for product value or conversion because BauData identified downloads as a relevant customer action. This assumption can be adjusted if BauData defines additional high-value actions in the future.

## Role

Product & Behavioral Data Analyst  
Tools: Python, pandas, scikit-learn, PostHog, Power BI, DAX, Excel
