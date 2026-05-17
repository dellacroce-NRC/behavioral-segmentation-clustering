# BauData B2B Usage Analytics & Behavioral Segmentation

## Executive Summary

Built an end-to-end product analytics workflow that transforms raw PostHog behavioral telemetry into a commercial prioritization system for BauData, a B2B platform.

The project moved from a descriptive clustering analysis to an operational dashboard that helps the commercial team answer a more valuable question: **which companies and users should receive attention first, and what action should be taken with each one?**

Instead of leaving the analysis at the user-segment level, the final version connects platform behavior with company/account data, enabling a B2B view of adoption, friction, usage value, and expansion opportunities.

## Business Impact

This project gives BauData a practical decision layer for commercial and customer success work:

- Prioritizes accounts with active users but no detected platform usage.
- Identifies companies already generating value signals and potential expansion opportunities.
- Detects users who explore the platform but do not complete the expected value action.
- Converts behavioral clusters into simple commercial labels and recommended actions.
- Reduces manual review by turning raw event/session data into ranked account and user lists.
- Supports more focused sales, onboarding, adoption, and retention conversations.

In practical terms, the dashboard helps the team move from **"we have usage data"** to **"these are the accounts we should activate, recover, maintain, or expand."**

## Key Results From The Latest Local Run

The current pipeline processed historical platform usage from PostHog and connected it with BauData's company/user master data.

| Area | Result |
|---|---:|
| Raw PostHog events processed | 52,191 |
| Raw PostHog sessions processed | 5,478 |
| Modeled active sessions | 5,441 |
| Unique users detected in usage data | 660 |
| Companies in the B2B master layer | 141 |
| Users with detected usage matched to company data | 191 |
| Active users without detected usage | 144 |
| Active companies without detected usage | 9 |
| Non-email usage IDs requiring better identity mapping | 420 |

These outputs exposed two commercially relevant realities:

1. Some active customer accounts have users who are registered but not showing detected usage, creating a clear adoption/onboarding opportunity.
2. A large share of PostHog activity still depends on improving identity resolution, because many usage IDs are technical or non-email identifiers that cannot yet be safely assigned to a company.

## What The Dashboard Enables

### 1. Company-Level Prioritization

The executive page helps the commercial team quickly identify:

- active companies with usage;
- active companies without detected usage;
- companies with downloads or stronger product value signals;
- companies with many active users still not using the platform;
- ranked accounts by commercial priority.

This creates a cleaner account-management workflow: instead of scanning spreadsheets or raw event exports, the team can focus first on the accounts with the strongest adoption, activation, or expansion signal.

### 2. User-Level Actionability

The user page translates account-level diagnosis into concrete user-level action:

- who is active but not using the product;
- who is exploring but not downloading;
- who shows high-value behavior;
- who may need onboarding or friction reduction;
- which users are good candidates for interviews, activation support, or success-case exploration.

### 3. Behavioral Evidence Behind Commercial Decisions

The clustering model is not presented as a technical artifact for its own sake. It is used as analytical evidence to classify behavior into interpretable user profiles, such as:

- Power User;
- Targeted/Search-oriented user;
- Rebound/Friction user;
- Risk or rage-click behavior.

This makes the commercial recommendations more defensible: actions are tied to observed behavior, not only to intuition.

## Analytical Approach

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
Power BI dashboard for commercial decision-making
```

## Commercial Scoring Logic

The scoring layer combines behavioral and business signals:

- active users without detected usage;
- users with high or medium activation opportunity;
- users in recovery/friction patterns;
- users with high-value behavior;
- download and usage signals.

Download behavior is treated as a proxy for product value because BauData identified downloads as an important customer action. The model is intentionally flexible: if the business later defines additional value actions, the scoring logic can incorporate them.

## Why This Project Matters

The value of the project is not only the clustering model. The stronger contribution is the translation of behavioral data into a usable commercial workflow.

For BauData, this means:

- faster identification of accounts needing activation;
- clearer visibility into companies not extracting value;
- better prioritization of commercial follow-up;
- stronger evidence for onboarding, retention, and expansion decisions;
- a reusable pipeline that can be refreshed as new PostHog data arrives.

For a product or growth team, the project demonstrates how product analytics can connect telemetry, behavioral segmentation, account management, and executive reporting in one workflow.

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

## Role & Tools

**Role:** Product & Behavioral Data Analyst  
**Tools:** Python, pandas, scikit-learn, PostHog, Power BI, DAX, Excel  
**Focus:** Product analytics, behavioral segmentation, B2B account prioritization, commercial decision support
