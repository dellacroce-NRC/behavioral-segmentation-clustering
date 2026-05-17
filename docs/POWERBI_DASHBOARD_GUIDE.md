# Power BI Dashboard Guide

## Recommended pages

### 1. Resumen Ejecutivo Empresas

Purpose: help the commercial team understand account-level opportunities quickly.

Recommended KPIs:

- Empresas Activas
- Empresas Activas Con Uso
- Empresas Activas Sin Uso
- Tasa Empresas Activas Con Uso
- Usuarios Activos Sin Uso
- Empresas Activas Con Descarga

Recommended visuals:

- prioritized company table;
- companies by commercial priority;
- companies with the highest number of active users without detected use;
- date slicer;
- company slicer;
- view selector for all companies vs priority segments.

### 2. Accion Comercial Usuarios

Purpose: move from the company/account level to specific users and recommended actions.

Recommended KPIs:

- Usuarios Activos
- Usuarios Activos Sin Uso
- Usuarios Con Uso
- Usuarios Oportunidad Activacion
- Usuarios Alto Valor
- Usuarios Con Descarga

Recommended visuals:

- prioritized user table;
- user usage scatter plot;
- users by recommended action;
- company slicer;
- user view selector.

## Color logic

Use consistent colors across pages:

- green: positive usage, confirmed use, high value;
- blue: neutral exploration or baseline usage;
- orange: activation opportunity;
- red: high-priority risk or no-use signal;
- gray: friction, monitoring, or inactive/no detected use.

## Interpretation principle

The dashboard should be explained as a commercial decision tool, not as a technical ML artifact.

Suggested narrative:

> First we identify which companies are active and whether they are actually using BauData. Then we prioritize accounts according to adoption, friction, download/value signals, and user behavior. Finally, the user page lets the commercial team see who explains each account's status and what action should be taken.
