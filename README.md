# Fuzzy DEMATEL Expert Evaluation Platform

A production-oriented Streamlit application that distributes the complete 18×18
direct-influence design across seven balanced respondent sets. It preserves the
scientific logic of Fuzzy DEMATEL while reducing individual respondent burden.

## Instrument contract

- Factors, in fixed order: `C1–C6`, `E1–E4`, `S1–S8`.
- Exactly 306 off-diagonal directions, partitioned once across seven sets.
- Set sizes: `44, 44, 44, 44, 44, 43, 43`.
- Every variable appears as a source and target 2–3 times in every set.
- Prompt: **To what extent does [Source Variable] influence [Target Variable]?**
- One relationship per screen with immediate Supabase autosave.
- Five linguistic values with exact triangular fuzzy numbers:

| Code | Meaning | TFN (l, m, u) |
|---|---|---|
| VL | Very Low Influence | (0.00, 0.00, 0.25) |
| LI | Low Influence | (0.00, 0.25, 0.50) |
| I | Moderate Influence | (0.25, 0.50, 0.75) |
| HI | High Influence | (0.50, 0.75, 1.00) |
| VH | Very High Influence | (0.75, 1.00, 1.00) |

`Cannot Assess` is also available. It has no TFN and is identified separately in
administrator coverage reports. Diagonal relationships are never assigned or
shown.

New respondents are assigned atomically to the set with the fewest completed
responses. Current assignment count breaks ties so simultaneous in-progress
respondents remain balanced.

## Architecture

```text
app.py                    Streamlit entry point and guarded page router
config.py                 Fixed factors, linguistic scale, research settings
research_content.py       Participant-facing wording from the approved workbook
models.py                 Typed domain records
questionnaire_sets.py     Audited seven-set relationship partition
validation.py             Expert code, set, response, and TFN validation
database.py               Assignment, autosave, completion, and admin repository
services.py               Secure Streamlit/Supabase composition
progress.py               Anonymous refresh-safe resume restoration
export.py                 Legacy and combined administrator exports
fuzzy_dematel.py          Input readers only; no calculations yet
components/
  layout.py               Shared navigation and visual system
  relationship_question.py Readable single-relationship response control
  matrix_grid.py          Retained, improved legacy matrix component
pages/
  admin.py                Password-protected coverage dashboard
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

The future mathematical engine can read the combined long-format export through
`fuzzy_dematel.load_distributed_export` without a database migration.

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
5. Configure `ADMIN_PASSWORD` (or `ADMIN_PASSWORD_SHA256`).

Streamlit executes Python on the server, so the key is not sent to the expert's
browser. The schema deliberately gives `anon` and `authenticated` no table
access. Never place the service-role key in source code, a public repository, or
client-side JavaScript.

The SQL migration seeds the audited 306-pair partition. An advisory-lock RPC
assigns sets atomically. Each response is upserted immediately, and a completion
RPC rejects incomplete sets, applies a common submission timestamp, and makes the
completed response set immutable. Database constraints verify set membership,
factor codes, direction, linguistic values, TFNs, and the no-diagonal rule.

The anonymous respondent UUID is retained in the page URL as `?respondent=...`.
Refreshing that URL reloads the assignment and all autosaved progress.

## Tests and quality checks

```bash
pytest
ruff check .
```

The test suite checks exact 306-pair coverage, set sizes, source/target balance,
all response controls, autosave, completion, TFN mapping, administrator exports,
Excel sheets, and round-trip loading through `fuzzy_dematel.py`.

## Export contract

Open `?admin=1` and authenticate to download:

- `fuzzy_dematel_all_responses.csv`: all raw responses from completed respondents.
- `fuzzy_dematel_complete_dataset.xlsx`, containing:
  - `Responses_Long`
  - `Relationship_Coverage`
  - `Evaluation_Count_Matrix`
  - `Set_Summary`
  - `Factor_Definitions`
  - `Metadata`

The relationship coverage sheet includes every off-diagonal direction even when
its count is zero. Rows are source variables and columns are target variables.
The export contains raw evaluations only; no fuzzy aggregation is performed.

Example future-engine input:

```python
from fuzzy_dematel import load_distributed_export

data = load_distributed_export("fuzzy_dematel_all_responses.csv")
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
6. Complete seven disposable pilots and confirm that every set is assigned once.
7. Verify autosave, refresh resume, submission, dashboard counts, and exports.

For live data collection, keep the repository private, restrict Supabase
dashboard membership, define a retention plan, and document backups under the
research data-management protocol.
