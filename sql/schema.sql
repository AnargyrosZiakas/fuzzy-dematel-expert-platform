-- Fuzzy DEMATEL Expert Evaluation Platform
-- Run once in the Supabase SQL editor before deploying the Streamlit app.

create extension if not exists pgcrypto;

create table if not exists public.expert_responses (
    submission_id uuid not null,
    expert_code text not null,
    timestamp timestamptz not null,
    from_factor text not null,
    to_factor text not null,
    linguistic_value text not null,
    tfn_l numeric(4, 2) not null,
    tfn_m numeric(4, 2) not null,
    tfn_u numeric(4, 2) not null,
    is_diagonal boolean not null,
    created_at timestamptz not null default timezone('utc', now()),
    primary key (submission_id, from_factor, to_factor),
    constraint expert_code_format check (
        expert_code ~ '^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$'
    ),
    constraint valid_from_factor check (
        from_factor in (
            'C1', 'C2', 'C3', 'C4', 'C5', 'C6',
            'E1', 'E2', 'E3', 'E4',
            'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8'
        )
    ),
    constraint valid_to_factor check (
        to_factor in (
            'C1', 'C2', 'C3', 'C4', 'C5', 'C6',
            'E1', 'E2', 'E3', 'E4',
            'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8'
        )
    ),
    constraint diagonal_flag_matches_pair check (
        is_diagonal = (from_factor = to_factor)
    ),
    constraint exact_linguistic_tfn_mapping check (
        (
            is_diagonal
            and linguistic_value = '0'
            and tfn_l = 0.00 and tfn_m = 0.00 and tfn_u = 0.00
        )
        or (
            not is_diagonal
            and (
                (linguistic_value = 'VL' and tfn_l = 0.00 and tfn_m = 0.00 and tfn_u = 0.25)
                or (linguistic_value = 'LI' and tfn_l = 0.00 and tfn_m = 0.25 and tfn_u = 0.50)
                or (linguistic_value = 'I'  and tfn_l = 0.25 and tfn_m = 0.50 and tfn_u = 0.75)
                or (linguistic_value = 'HI' and tfn_l = 0.50 and tfn_m = 0.75 and tfn_u = 1.00)
                or (linguistic_value = 'VH' and tfn_l = 0.75 and tfn_m = 1.00 and tfn_u = 1.00)
            )
        )
    )
);

create index if not exists expert_responses_timestamp_idx
    on public.expert_responses (timestamp desc);

create index if not exists expert_responses_expert_code_idx
    on public.expert_responses (expert_code);

-- Enforce the scientific instrument boundary at database level. Each insert
-- statement must contain one complete 18×18 matrix with a single UUID, expert
-- code, and timestamp. Any violation raises an exception and rolls back.
create or replace function public.validate_expert_matrix_batch()
returns trigger
language plpgsql
set search_path = public
as $$
declare
    row_count integer;
    pair_count integer;
    submission_count integer;
    expert_count integer;
    timestamp_count integer;
    diagonal_count integer;
begin
    select
        count(*),
        count(distinct (from_factor, to_factor)),
        count(distinct submission_id),
        count(distinct expert_code),
        count(distinct timestamp),
        count(*) filter (where is_diagonal)
    into
        row_count,
        pair_count,
        submission_count,
        expert_count,
        timestamp_count,
        diagonal_count
    from new_matrix_rows;

    if row_count <> 324
       or pair_count <> 324
       or submission_count <> 1
       or expert_count <> 1
       or timestamp_count <> 1
       or diagonal_count <> 18 then
        raise exception
            'A submission must contain one complete 324-cell matrix (18 diagonal, 306 off-diagonal).';
    end if;
    return null;
end;
$$;

drop trigger if exists validate_expert_matrix_insert
    on public.expert_responses;

create trigger validate_expert_matrix_insert
after insert on public.expert_responses
referencing new table as new_matrix_rows
for each statement
execute function public.validate_expert_matrix_batch();

alter table public.expert_responses enable row level security;

-- No anon/authenticated policies are intentionally created. The Streamlit
-- server uses the Supabase service-role key from encrypted server-side secrets;
-- clients never receive that key. Keep this table write-only from the public API.
revoke all on table public.expert_responses from anon, authenticated;

comment on table public.expert_responses is
    'Complete 18×18 Fuzzy DEMATEL expert matrices in canonical long format.';

