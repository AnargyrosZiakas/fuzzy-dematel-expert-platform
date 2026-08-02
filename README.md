# Fuzzy DEMATEL Expert Evaluation Platform

A production-oriented Streamlit application for collecting one fixed 18×18
direct-influence matrix per expert. It preserves the scientific logic of Fuzzy
DEMATEL: every off-diagonal ordered pair is required, direction matters, and the
diagonal is fixed at zero.

## Instrument contract

- Factors, in fixed order: `C1–C6`, `E1–E4`, `S1–S8`.
- Prompt: **How much does the ROW factor influence the COLUMN factor?**
- 324 stored records per submission: 306 expert judgments and 18 zero diagonals.
- Five linguistic values with exact triangular fuzzy numbers:

| Code | Meaning | TFN (l, m, u) |
|---|---|---|
| VL | Very Low Influence | (0.00, 0.00, 0.25) |
| LI | Low Influence | (0.00, 0.25, 0.50) |
| I | Influence | (0.25, 0.50, 0.75) |
| HI | High Influence | (0.50, 0.75, 1.00) |
| VH | Very High Influence | (0.75, 1.00, 1.00) |

The UI, Python validation layer, export layer, and PostgreSQL constraints all
enforce the same contract.

## Architecture

```text
app.py                    Streamlit entry point and guarded page router
config.py                 Fixed factors, linguistic scale, research settings
research_content.py       Participant-facing wording from the approved workbook
models.py                 Typed domain records
validation.py             Expert code and 306-comparison validation
database.py               Write-only Supabase persistence adapter
export.py                 Long/wide CSV and Excel generation
fuzzy_dematel.py          Input readers only; no calculations yet
components/
  layout.py               Shared navigation and visual system
  matrix_grid.py          18×18 matrix component
pages/
  welcome.py
  research.py
  consent.py
  expert_code.py
  matrix.py
  submit.py
data/factors.csv          Ordered dimensions, criteria, and tooltip definitions
sql/schema.sql            Supabase table, constraints, trigger, and RLS
tests/                    Validation, persistence, and export round trips
```

The future mathematical engine can be implemented inside `fuzzy_dematel.py`
without changing either the database table or current exports.

## Research text configuration

The study title, invitation, method instructions, consent statement, researcher
details, and closing message are centralized in `research_content.py`. The 18
approved criterion names and definitions are stored in `data/factors.csv`. Text
can be revised there without changing matrix validation, database storage, or
export logic. The order and `factor_code` values must not change.

These metadata values can optionally be overridden through environment variables
or Streamlit Cloud settings:

- `STUDY_TITLE`
- `RESEARCH_DESCRIPTION`
- `RESEARCHER_NAME`
- `RESEARCH_CONTACT_EMAIL`

Any participant-facing revision should remain consistent with the study's
approved research and data-management protocol.

## Local setup (Python 3.12)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app.py
```

Do not commit `.streamlit/secrets.toml`; it is ignored by Git.

## Supabase setup

1. Create a Supabase project.
2. Open its SQL editor and run `sql/schema.sql` once.
3. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
4. Add the project URL and **service-role key**.

Streamlit executes Python on the server, so the key is not sent to the expert's
browser. The schema deliberately gives `anon` and `authenticated` no table
access. Never place the service-role key in source code, a public repository, or
client-side JavaScript.

Each app submission is one PostgREST bulk insert. The database statement trigger
rejects and rolls back anything other than exactly one 324-cell matrix with 18
diagonal rows, one UUID, one expert code, and one timestamp. Row constraints also
verify every factor, diagonal flag, linguistic code, and TFN value.

## Tests and quality checks

```bash
pytest
ruff check .
```

The test suite checks all 306 required comparisons, all 18 zero diagonals, exact
TFN mapping, database bulk-write behavior, file schemas, Excel sheets, and
round-trip loading through `fuzzy_dematel.py`.

## Export contract

After a successful submission, four files are generated automatically:

- `*_long.csv`: canonical 324-row database layout.
- `*_wide.csv`: 18×18 linguistic matrix; first column is `from_factor`.
- `*_long.xlsx`: `Long_Data`, `Metadata`, and `Factor_Definitions` sheets.
- `*_wide.xlsx`: `Linguistic`, `TFN_L`, `TFN_M`, `TFN_U`, `Metadata`, and
  `Factor_Definitions` sheets.

All matrices use rows as influencing factors and columns as influenced factors.
The three TFN sheets are numeric 18×18 matrices suitable for NumPy.

Example future-engine input:

```python
from fuzzy_dematel import load_long_export, tfn_arrays_from_long

data = load_long_export("fuzzy_dematel_<uuid>_long.csv")
lower, modal, upper = tfn_arrays_from_long(data)
```

These functions validate and load data only. Mathematical Fuzzy DEMATEL
normalization, total-relation matrices, defuzzification, and cause/effect
calculations are intentionally not implemented.

## Streamlit Community Cloud deployment

1. Push this repository to a private Git host.
2. Create a Streamlit Community Cloud app with `app.py` as the entry point.
3. Paste the contents of `.streamlit/secrets.toml` into the app's encrypted
   Secrets settings.
4. Add the study metadata values to the app environment.
5. Confirm the factor definitions and approved consent wording.
6. Submit one disposable pilot matrix and verify exactly 324 rows in Supabase.

For live data collection, keep the repository private, restrict Supabase
dashboard membership, define a retention plan, and document backups under the
research data-management protocol.
