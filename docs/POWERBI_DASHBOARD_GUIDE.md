# Power BI Dashboard Guide

## Dashboard purpose

The report is designed as a commercial decision tool, not as a technical machine-learning artifact. It helps the team identify which companies and users deserve attention first, why they matter, and which action should follow.

## Pages

### 1. Resumen Ejecutivo Empresas

Purpose: give commercial leadership a fast account-level view of adoption, non-usage, download/value signals, and prioritization.

Current KPIs:

- Empresas Activas
- Empresas Activas Con Uso
- Empresas Activas Sin Uso
- Tasa Empresas Activas Con Uso
- Empresas Activas Sin Descarga
- Empresas Activas Con Descarga

Recommended visuals:

- prioritized company table;
- companies by commercial priority;
- companies with the highest number of active users without detected use;
- date slicer;
- company slicer;
- view selector for all companies, prioritized companies, companies with use, companies without use, companies with downloads, and companies without downloads.

### 2. Accion Comercial Usuarios

Purpose: move from the company/account level to specific users and recommended actions.

Current KPIs:

- Usuarios Activos
- Usuarios Activos Sin Uso
- Usuarios Con Uso
- Usuarios Oportunidad Activacion
- Usuarios Alto Valor
- Usuarios Activos Con Descarga
- Usuarios Activos Sin Descarga

Recommended visuals:

- prioritized user table;
- user usage scatter plot;
- users by recommended action;
- company slicer;
- user view selector for all users, prioritized users, active users, active users without use, users with use, activation opportunities, high-value users, users with downloads, and users without downloads.

## Selector logic

The selector should not duplicate the default table state.

- On the company page, the default table is the prioritized account list; the selector still allows switching to all companies and specific commercial segments.
- On the user page, the default table is all users; the selector allows switching to prioritized users and specific behavioral/commercial segments.

This avoids a dead option where selecting a slicer value does not visibly change the table.

## Date filtering

Date slicers should be synchronized across pages when comparable KPIs are expected. If a KPI does not react to the date range, check whether the DAX measure is intentionally ignoring date context or whether the slicer is only scoped to the current page.

## Color logic

Use consistent colors across pages:

- green: positive usage, confirmed use, high value;
- blue: neutral exploration or baseline usage;
- orange: activation opportunity;
- red: high-priority risk or no-use signal;
- gray: friction, monitoring, or inactive/no detected use.

## Interpretation principle

Suggested narrative:

> First we identify which companies are active and whether they are actually using BauData. Then we prioritize accounts according to adoption, friction, download/value signals, and user behavior. Finally, the user page lets the commercial team see who explains each account's status and what action should be taken.
