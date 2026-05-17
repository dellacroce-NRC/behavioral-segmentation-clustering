# Project Overview

## Why this project changed

The first version of this repository was closer to an academic/product strategy case. It included broader material such as landing-page analysis and UX audit work.

The current version focuses on the platform usage problem:

- identifying behavioral patterns from PostHog telemetry;
- validating whether K-Means is a reasonable clustering choice;
- translating user-level behavior into company-level commercial decisions;
- preparing a Power BI dashboard for executive B2B decision-making.

## What the dashboard is meant to do

The dashboard is not designed as a purely technical clustering report. Its purpose is commercial prioritization.

The main story is:

1. Start with companies: which accounts are active, inactive, using the platform, not using it, or showing value signals.
2. Drill down into users: which specific users explain the company's status and what action should be taken.
3. Use clustering as analytical support: profiles help interpret behavior, but the decision layer is framed in business language.

## Key analytical concepts

### Active company

A company is considered active when the company master file marks it as having active users. This comes from the business/customer dataset, not directly from PostHog behavior.

### Company with use

A company has detected use when at least one mapped user has sessions or interaction data in the PostHog-derived usage table.

### Active company without use

This is a high-priority adoption signal: the company has active registered users, but those users do not show detected platform usage in the analyzed period.

### Download as value proxy

Downloads are treated as a proxy for conversion or product value because BauData indicated that many customers use the platform to extract and share information internally.

This is a modeling assumption, not a fixed truth. If BauData defines other key actions, the scoring logic can incorporate them.

## Modeling decision

K-Means with three clusters is kept as the operational model because it gives a simple and explainable segmentation structure. Other clustering options were explored, but the chosen model is easier to communicate and align with commercial actions.

The clusters are not the final business answer. They are an analytical input used to classify user behavior into profiles such as:

- Power User;
- Buscador Puntual;
- Rebote / Friccion;
- Riesgo / Rage Clicks.

## Repository scope

This repository contains reproducible code and documentation. It intentionally does not include private data, credentials, real customer exports, or Power BI files with embedded sensitive information.
