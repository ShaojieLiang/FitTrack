# Publication boundary

This repository starts with a new Git history and invented data. It does not contain a personal project's images, database, profile, diet, authorization text, credentials, API receipts or account-specific identifiers.

- Committed demonstration images are rendered from the deterministic synthetic generator.
- `private/`, `data/`, `outputs/`, `.env`, `.secrets/` and databases are ignored.
- `.env.example` contains empty endpoint and token definitions only. No real service addresses, API paths or credentials are bundled. Users configure their own private servers using the documented normalized contract.
- `demo --publish docs` permits publication only after checking that the demo database contains synthetic sources exclusively. It regenerates its dedicated synthetic projection before exporting.
- `scripts/check_public.py` checks staged and unignored paths, known token patterns, local user paths and public artifact source labels. It reports paths and reasons, never matched secret values.
- GitHub Actions run the same core tests, public-file scan and offline demo without account credentials.

An ignore rule or pattern scanner cannot prove the absence of all personal information. Review the staged file list and the rendered assets before publishing changes. Never use `git add -f` to include private files. If credentials were ever committed, revoke/rotate them; deleting a working-tree file does not remove existing copies or Git history.

No license is asserted over Xunji's API, developer documents or third-party data. This repository does not redistribute private provider instructions. A project license is intentionally not selected on the owner's behalf in this initial publication.
