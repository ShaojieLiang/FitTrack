# FitTrack development

- Public portfolio project. All committed fixtures, images and evaluations must be synthetic and labeled.
- Never read or import another local project's personal records, credentials or screenshots.
- Live data belongs only in ignored `private/`. Credentials come from scoped environment variables.
- Server integration is opt-in and read-only. Bundle only blank endpoint configuration; never commit real service addresses, API routes or credentials. Never introduce automatic cloud writes or scheduled jobs.
- Preserve missingness, measurement units, set labels and date provenance. Unknown equipment/sets cannot qualify for comparable predictions.
- Forecast features must precede target dates; preprocessing fits on each training window only.
- Distinguish synthetic software verification, real predictive accuracy and causal training benefits.
- Before publication run core tests, the demo, and `python scripts/check_public.py`; review the staged file list.
