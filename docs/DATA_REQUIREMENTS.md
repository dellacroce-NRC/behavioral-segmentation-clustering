# Data Requirements

The pipeline expects local private inputs that are not committed to GitHub.

## PostHog exports

Expected local output from `scripts/posthog_historico_local.py`:

```text
data/posthog_raw/full/posthog_events_YYYY_MM_DD_a_YYYY_MM_DD.csv
data/posthog_raw/full/posthog_sessions_YYYY_MM_DD_a_YYYY_MM_DD.csv
```

Expected event columns:

- `distinct_id`
- `event`
- `screen`
- `sub_screen`
- `action`
- `datetime`
- `timestamp`

Expected session columns:

- `distinct_id`
- `start`
- `end`
- `max_insert`
- `duration`
- `$start_timestamp`

## Company/user master

Expected local file:

```text
data/company_master/usuarios_baudata_YYYY-MM-DD.xlsx
```

Minimum expected columns:

- user e-mail;
- company name;
- user status.

The current processing script expects column names equivalent to:

- `user`
- `empresa`
- `status`

## Privacy note

These files can contain customer names, user e-mails, internal usage behavior, and business-sensitive information. Keep them local unless BauData explicitly authorizes sharing anonymized samples.
