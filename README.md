# Fuzzy DEMATEL Expert Evaluation Platform

A production-oriented Streamlit application for a hierarchical Fuzzy DEMATEL
expert questionnaire. The instrument presents four manageable matrices and stores
every directional judgement in Supabase as it is selected.

## Scientific instrument contract

The respondent completes the following fixed matrices:

| Stage | Matrix | Size | Directed answers |
|---|---|---:|---:|
| 1 | Consumer-Cultural & Behavioural (`C1–C6`) | 6 × 6 | 30 |
| 2 | Economic & Market (`E1–E4`) | 4 × 4 | 12 |
| 3 | Airline Strategic & Operational (`S1–S7`) | 7 × 7 | 42 |
| 4 | Relationships Between Dimensions (`C`, `E`, `S`) | 3 × 3 | 6 |
|  | **Total** |  | **90** |

Diagonal self-influence cells are disabled and never stored as respondent answers.
Level 1 contains only within-dimension criterion relationships: individual
cross-dimensional pairs such as `C1 → E2` do not exist in the questionnaire.
The original 18 × 18 matrix and the earlier seven-set questionnaire are not shown
to new respondents.

The direction is always **ROW/source/cause → COLUMN/target/affected factor**. Each
direction is distinct.

### Linguistic scale

| Code | Participant-facing meaning | TFN `(l, m, u)` |
|---|---|---|
| VL | Very Low Influence | `(0.00, 0.00, 0.25)` |
| LI | Low Influence | `(0.00, 0.25, 0.50)` |
| I | Influence | `(0.25, 0.50, 0.75)` |
| HI | High Influence | `(0.50, 0.75, 1.00)` |
| VH | Very High Influence | `(0.75, 1.00, 1.00)` |

Participants see only the linguistic choices. `Cannot Assess` is not part of the
hierarchical instrument.

## Respondent experience

- Welcome, research information, consent and anonymous expert code
- One matrix at a time with Previous/Continue navigation
- Current-matrix and overall progress indicators
- Explicit row/column direction guidance and an active relationship panel
- Expandable criteria definitions and header tooltips
- A five-option scale selector; completed cells retain a bold acronym
- Immediate Supabase autosave after every valid selection
- Refresh-safe recovery through `?respondent=<anonymous-uuid>`
- Section-level review before final submission
- Database and UI checks that block incomplete submission

No account or participant authentication is required.

## Architecture

```text
app.py                         Streamlit entry point and guarded page router
config.py                      Instrument constants and exact TFN scale
research_content.py            Approved participant-facing research wording
models.py                      Typed domain records and matrix definitions
hierarchical_questionnaire.py  Data-driven 30 + 12 + 42 + 6 pair catalogue
validation.py                  Expert-code, relationship and completeness checks
database.py                    Supabase sessions, autosave, completion and admin I/O
services.py                    Secure Streamlit/Supabase composition
progress.py                    Anonymous refresh-safe restoration
export.py                      Current and historical CSV/Excel exports
fuzzy_dematel.py               Validated input adapters; no calculations
components/
  fuzzy_matrix.py              Matrix cells, selector, active panel and references
  layout.py                    Navigation and the academic visual system
pages/
  admin.py                     Password-protected dashboard and downloads
  welcome.py
  research.py
  consent.py
  expert_code.py
  matrix.py
  submit.py
data/factors.csv               Historical 18-variable definitions
data/hierarchical_factors.csv  Current 17-criterion names and definitions
sql/
  schema.sql                   Historical seven-set schema retained for compatibility
  hierarchical_migration.sql   Fresh-install four-matrix schema and completion RPC
  hierarchical_v2_migration.sql  Safe 104-to-90 relationship upgrade
tests/                         Scientific, UI, storage and export verification
```

The old `questionnaire_assignments`, `questionnaire_relationships` and
`expert_responses` tables remain available for historical data. New collection is
isolated in `hierarchical_questionnaires`, `hierarchical_relationships` and
`hierarchical_responses`, preventing incompatible study designs from being mixed.

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

## Supabase migration

For an existing `hierarchical_v1` deployment, run:

```text
sql/hierarchical_v2_migration.sql
```

For a completely new Supabase project, run `sql/schema.sql` first and then
`sql/hierarchical_migration.sql`. The hierarchical migration is idempotent and
does not delete or alter historical responses.

Required encrypted Streamlit secrets:

```toml
SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_KEY = "your-service-role-key"
SUPABASE_SCHEMA = "public"
ADMIN_PASSWORD = "a-long-random-password"
```

Optional table-name overrides are documented in
`.streamlit/secrets.toml.example`. The service-role key remains on the Streamlit
server; it must never be committed or exposed in client-side code. Row-level
security denies direct `anon` and `authenticated` access.

The current design seeds exactly 90 allowed relationships. Foreign keys prevent
diagonal, cross-dimensional or unknown pairs. A trigger verifies respondent code,
criterion names and mutable session status. The completion RPC rejects any session
without exactly 90 saved responses and makes completed answers immutable.

## Administrator dashboard and export

Open `?admin=1` and authenticate with the configured administrator password. The
dashboard reports:

- completed and in-progress anonymous respondents;
- evaluations collected per matrix;
- count for every one of the 90 directed relationships;
- relationships below the configured minimum evaluation threshold;
- separate access to historical seven-set exports.

Current downloads:

- `fuzzy_dematel_hierarchical_responses.csv`: analysis-ready long rows from
  completed respondents only;
- `fuzzy_dematel_hierarchical_dataset.xlsx`, containing:
  - `Responses_Long`
  - `Responses_Wide` (one respondent per row, 90 linguistic columns)
  - `Relationship_Coverage`
  - `Respondent_Summary`
  - `Matrix_Summary`
  - `Cultural_Counts`, `Economic_Counts`, `Strategic_Counts`, `Dimension_Counts`
  - `Criteria_Definitions`
  - `Metadata`

Each long row includes the anonymous respondent ID, expert code, matrix ID, source
and target codes/names, linguistic response, all three TFN values and timestamp.
No missing response is calculated or invented.

The future mathematical module can reconstruct all four TFN matrices for one
completed respondent without changing the database:

```python
from fuzzy_dematel import (
    hierarchical_tfn_matrices_from_long,
    load_hierarchical_export,
)

data = load_hierarchical_export("fuzzy_dematel_hierarchical_responses.csv")
matrices = hierarchical_tfn_matrices_from_long(data, respondent_id="...")
```

These functions only validate and reshape input. Fuzzy DEMATEL normalization,
aggregation, defuzzification and causal calculations are intentionally not
implemented.

## Tests and quality checks

```bash
pytest
ruff check .
```

The tests verify the exact `30 + 12 + 42 + 6 = 90` relationship contract, no
diagonal or cross-dimensional criterion pairs, all five TFN mappings, autosave UI,
visible cell acronyms, navigation, completion blocking, Supabase adapter behavior,
CSV/Excel readability and reconstruction into `(6,6)`, `(4,4)`, `(7,7)` and
`(3,3)` TFN arrays.

## Streamlit Community Cloud deployment

1. Run `sql/hierarchical_v2_migration.sql` for an existing v1 deployment, or
   `sql/hierarchical_migration.sql` for a fresh hierarchical deployment.
2. Push this repository to the GitHub branch used by Streamlit Community Cloud.
3. Keep the existing app entry point as `app.py` and Python runtime as 3.12.
4. Confirm encrypted Supabase and administrator secrets remain configured.
5. Reboot the Streamlit app and complete a disposable 90-answer pilot.
6. Verify refresh recovery, final submission, dashboard counts, CSV and Excel.

For live dissertation data, restrict Supabase dashboard membership, maintain a
backup/retention plan and document the process in the approved data-management
protocol.
