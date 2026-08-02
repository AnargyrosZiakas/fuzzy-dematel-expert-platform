-- Fuzzy DEMATEL Expert Evaluation Platform
-- Idempotent migration for seven distributed questionnaire sets.
-- Run in the Supabase SQL editor before deploying this application version.

create extension if not exists pgcrypto;

create table if not exists public.questionnaire_assignments (
    respondent_id uuid primary key,
    expert_code text not null,
    set_id smallint not null check (set_id between 1 and 7),
    status text not null default 'in_progress'
        check (status in ('in_progress', 'completed')),
    started_at timestamptz not null default now(),
    completed_at timestamptz,
    constraint assignment_expert_code_format check (
        expert_code ~ '^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$'
    ),
    constraint assignment_completion_state check (
        (status = 'in_progress' and completed_at is null)
        or (status = 'completed' and completed_at is not null)
    )
);

create table if not exists public.questionnaire_relationships (
    set_id smallint not null check (set_id between 1 and 7),
    position smallint not null,
    source_factor text not null,
    target_factor text not null,
    primary key (source_factor, target_factor),
    unique (set_id, position),
    unique (set_id, source_factor, target_factor),
    constraint relationship_not_diagonal check (source_factor <> target_factor)
);

-- The explicit matrix is identical to questionnaire_sets.SET_ASSIGNMENT_MATRIX.
-- Rows/columns follow C1–C6, E1–E4, S1–S8; 0 marks the diagonal.
with factor_codes(code, factor_index) as (
    values
        ('C1', 1), ('C2', 2), ('C3', 3), ('C4', 4), ('C5', 5), ('C6', 6),
        ('E1', 7), ('E2', 8), ('E3', 9), ('E4', 10),
        ('S1', 11), ('S2', 12), ('S3', 13), ('S4', 14),
        ('S5', 15), ('S6', 16), ('S7', 17), ('S8', 18)
), assignment_rows(row_index, assignments) as (
    values
        (1,  '041356352726771451'),
        (2,  '303422777661154514'),
        (3,  '320256461377245561'),
        (4,  '566077124371536244'),
        (5,  '114302643736742525'),
        (6,  '512760235641416735'),
        (7,  '261143066213557472'),
        (8,  '742325101563523647'),
        (9,  '553157310442617236'),
        (10, '274561145074362723'),
        (11, '637615422502431317'),
        (12, '163614723450675372'),
        (13, '132574532764064156'),
        (14, '475741243125206163'),
        (15, '747634651517320232'),
        (16, '426273376155173054'),
        (17, '457431417235325606'),
        (18, '675136574344112620')
), expanded as (
    select
        substring(ar.assignments from target.factor_index for 1)::smallint as set_id,
        source.code as source_factor,
        target.code as target_factor,
        source.factor_index as source_index,
        target.factor_index as target_index
    from assignment_rows ar
    join factor_codes source on source.factor_index = ar.row_index
    cross join factor_codes target
    where source.factor_index <> target.factor_index
), numbered as (
    select
        set_id,
        row_number() over (
            partition by set_id order by source_index, target_index
        )::smallint as position,
        source_factor,
        target_factor
    from expanded
)
insert into public.questionnaire_relationships (
    set_id, position, source_factor, target_factor
)
select set_id, position, source_factor, target_factor
from numbered
on conflict (source_factor, target_factor) do update
set set_id = excluded.set_id,
    position = excluded.position;

create table if not exists public.expert_responses (
    submission_id uuid not null,
    expert_code text not null,
    set_id smallint,
    timestamp timestamptz not null,
    from_factor text not null,
    source_variable_name text,
    to_factor text not null,
    target_variable_name text,
    linguistic_value text not null,
    tfn_l numeric(4, 2),
    tfn_m numeric(4, 2),
    tfn_u numeric(4, 2),
    is_diagonal boolean not null default false,
    created_at timestamptz not null default now(),
    primary key (submission_id, from_factor, to_factor)
);

-- Safely evolve an existing full-matrix installation without deleting history.
alter table public.expert_responses
    add column if not exists set_id smallint,
    add column if not exists source_variable_name text,
    add column if not exists target_variable_name text;

alter table public.expert_responses alter column tfn_l drop not null;
alter table public.expert_responses alter column tfn_m drop not null;
alter table public.expert_responses alter column tfn_u drop not null;

drop trigger if exists validate_expert_matrix_insert
    on public.expert_responses;
drop function if exists public.validate_expert_matrix_batch();

alter table public.expert_responses
    drop constraint if exists expert_code_format,
    drop constraint if exists valid_from_factor,
    drop constraint if exists valid_to_factor,
    drop constraint if exists diagonal_flag_matches_pair,
    drop constraint if exists exact_linguistic_tfn_mapping,
    drop constraint if exists valid_questionnaire_set,
    drop constraint if exists distributed_names_required;

alter table public.expert_responses
    add constraint expert_code_format check (
        expert_code ~ '^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$'
    ),
    add constraint valid_from_factor check (
        from_factor in (
            'C1', 'C2', 'C3', 'C4', 'C5', 'C6',
            'E1', 'E2', 'E3', 'E4',
            'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8'
        )
    ),
    add constraint valid_to_factor check (
        to_factor in (
            'C1', 'C2', 'C3', 'C4', 'C5', 'C6',
            'E1', 'E2', 'E3', 'E4',
            'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8'
        )
    ),
    add constraint diagonal_flag_matches_pair check (
        is_diagonal = (from_factor = to_factor)
    ),
    add constraint valid_questionnaire_set check (
        set_id is null or set_id between 1 and 7
    ),
    add constraint distributed_names_required check (
        set_id is null
        or (
            source_variable_name is not null
            and target_variable_name is not null
            and not is_diagonal
        )
    ),
    add constraint exact_linguistic_tfn_mapping check (
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
                or (linguistic_value = 'Cannot Assess' and tfn_l is null and tfn_m is null and tfn_u is null)
            )
        )
    );

do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'response_relationship_membership'
    ) then
        alter table public.expert_responses
            add constraint response_relationship_membership
            foreign key (set_id, from_factor, to_factor)
            references public.questionnaire_relationships (
                set_id, source_factor, target_factor
            ) not valid;
    end if;
    if not exists (
        select 1 from pg_constraint
        where conname = 'response_assignment_membership'
    ) then
        alter table public.expert_responses
            add constraint response_assignment_membership
            foreign key (submission_id)
            references public.questionnaire_assignments (respondent_id)
            not valid;
    end if;
end;
$$;

create index if not exists expert_responses_timestamp_idx
    on public.expert_responses (timestamp desc);
create index if not exists expert_responses_set_idx
    on public.expert_responses (set_id, from_factor, to_factor);
create index if not exists questionnaire_assignments_balance_idx
    on public.questionnaire_assignments (set_id, status);

create or replace function public.validate_distributed_response()
returns trigger
language plpgsql
set search_path = public
as $$
declare
    assigned_set smallint;
    assigned_code text;
    assignment_status text;
begin
    if new.set_id is null then
        return new; -- Preserve compatibility with historical full matrices.
    end if;

    select qa.set_id, qa.expert_code, qa.status
    into assigned_set, assigned_code, assignment_status
    from public.questionnaire_assignments qa
    where qa.respondent_id = new.submission_id;

    if not found then
        raise exception 'No questionnaire assignment exists for this respondent.';
    end if;
    if assigned_set <> new.set_id or assigned_code <> new.expert_code then
        raise exception 'Response does not match the respondent assignment.';
    end if;
    if assignment_status = 'completed' then
        raise exception 'Completed questionnaire responses are immutable.';
    end if;
    if new.from_factor = new.to_factor or new.is_diagonal then
        raise exception 'Diagonal relationships cannot be evaluated.';
    end if;
    return new;
end;
$$;

drop trigger if exists validate_distributed_response_write
    on public.expert_responses;
create trigger validate_distributed_response_write
before insert or update on public.expert_responses
for each row execute function public.validate_distributed_response();

create or replace function public.assign_questionnaire_set(
    p_respondent_id uuid,
    p_expert_code text
)
returns table (
    respondent_id uuid,
    expert_code text,
    set_id smallint,
    status text,
    started_at timestamptz,
    completed_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
declare
    selected_set smallint;
begin
    if p_expert_code !~ '^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$' then
        raise exception 'Invalid anonymous expert code.';
    end if;

    perform pg_advisory_xact_lock(hashtext('fuzzy_dematel_set_assignment'));

    if exists (
        select 1 from public.questionnaire_assignments qa
        where qa.respondent_id = p_respondent_id
    ) then
        return query
        select qa.respondent_id, qa.expert_code, qa.set_id, qa.status,
               qa.started_at, qa.completed_at
        from public.questionnaire_assignments qa
        where qa.respondent_id = p_respondent_id;
        return;
    end if;

    select candidate.set_id
    into selected_set
    from (
        select
            generated.set_id::smallint as set_id,
            count(qa.respondent_id) filter (
                where qa.status = 'completed'
            ) as completed_count,
            count(qa.respondent_id) as assignment_count
        from generate_series(1, 7) generated(set_id)
        left join public.questionnaire_assignments qa
            on qa.set_id = generated.set_id
        group by generated.set_id
    ) candidate
    order by candidate.completed_count,
             candidate.assignment_count,
             candidate.set_id
    limit 1;

    insert into public.questionnaire_assignments (
        respondent_id, expert_code, set_id
    ) values (
        p_respondent_id, p_expert_code, selected_set
    );

    return query
    select qa.respondent_id, qa.expert_code, qa.set_id, qa.status,
           qa.started_at, qa.completed_at
    from public.questionnaire_assignments qa
    where qa.respondent_id = p_respondent_id;
end;
$$;

create or replace function public.complete_questionnaire_assignment(
    p_respondent_id uuid
)
returns table (
    respondent_id uuid,
    expert_code text,
    set_id smallint,
    status text,
    started_at timestamptz,
    completed_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
declare
    assignment_row public.questionnaire_assignments%rowtype;
    expected_count integer;
    response_count integer;
    completion_time timestamptz;
begin
    select * into assignment_row
    from public.questionnaire_assignments qa
    where qa.respondent_id = p_respondent_id
    for update;

    if not found then
        raise exception 'Questionnaire assignment not found.';
    end if;
    if assignment_row.status = 'completed' then
        return query
        select qa.respondent_id, qa.expert_code, qa.set_id, qa.status,
               qa.started_at, qa.completed_at
        from public.questionnaire_assignments qa
        where qa.respondent_id = p_respondent_id;
        return;
    end if;

    select count(*) into expected_count
    from public.questionnaire_relationships qr
    where qr.set_id = assignment_row.set_id;

    select count(*) into response_count
    from public.expert_responses er
    where er.submission_id = p_respondent_id
      and er.set_id = assignment_row.set_id
      and not er.is_diagonal
      and er.linguistic_value in (
          'VL', 'LI', 'I', 'HI', 'VH', 'Cannot Assess'
      );

    if expected_count not between 43 and 45
       or response_count <> expected_count then
        raise exception
            'The assigned questionnaire set is incomplete (% of % responses).',
            response_count, expected_count;
    end if;

    completion_time := now();
    update public.expert_responses
    set timestamp = completion_time
    where submission_id = p_respondent_id
      and set_id = assignment_row.set_id;

    update public.questionnaire_assignments
    set status = 'completed', completed_at = completion_time
    where questionnaire_assignments.respondent_id = p_respondent_id;

    return query
    select qa.respondent_id, qa.expert_code, qa.set_id, qa.status,
           qa.started_at, qa.completed_at
    from public.questionnaire_assignments qa
    where qa.respondent_id = p_respondent_id;
end;
$$;

alter table public.questionnaire_assignments enable row level security;
alter table public.questionnaire_relationships enable row level security;
alter table public.expert_responses enable row level security;

revoke all on table public.questionnaire_assignments from anon, authenticated;
revoke all on table public.questionnaire_relationships from anon, authenticated;
revoke all on table public.expert_responses from anon, authenticated;
revoke all on function public.assign_questionnaire_set(uuid, text)
    from public, anon, authenticated;
revoke all on function public.complete_questionnaire_assignment(uuid)
    from public, anon, authenticated;

grant all on table public.questionnaire_assignments to service_role;
grant select on table public.questionnaire_relationships to service_role;
grant all on table public.expert_responses to service_role;
grant execute on function public.assign_questionnaire_set(uuid, text)
    to service_role;
grant execute on function public.complete_questionnaire_assignment(uuid)
    to service_role;

comment on table public.questionnaire_assignments is
    'Anonymous balanced-set assignments and completion state.';
comment on table public.questionnaire_relationships is
    'Audited partition of all 306 off-diagonal directed relationships.';
comment on table public.expert_responses is
    'Autosaved distributed Fuzzy DEMATEL responses; legacy rows are retained.';
