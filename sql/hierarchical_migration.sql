-- Fuzzy DEMATEL Expert Evaluation Platform
-- Idempotent migration for the hierarchical four-matrix questionnaire.
-- Run after sql/schema.sql on a new project, or run this file alone on the
-- existing seven-set project. Historical tables and responses are not modified.

create extension if not exists pgcrypto;

create table if not exists public.hierarchical_questionnaires (
    respondent_id uuid primary key,
    expert_code text not null,
    design_version text not null default 'hierarchical_v1'
        check (design_version = 'hierarchical_v1'),
    status text not null default 'in_progress'
        check (status in ('in_progress', 'completed')),
    started_at timestamptz not null default now(),
    completed_at timestamptz,
    constraint hierarchical_expert_code_format check (
        expert_code ~ '^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$'
    ),
    constraint hierarchical_completion_state check (
        (status = 'in_progress' and completed_at is null)
        or (status = 'completed' and completed_at is not null)
    )
);

create table if not exists public.hierarchical_relationships (
    matrix_id text not null check (
        matrix_id in ('cultural', 'economic', 'strategic', 'dimension_level')
    ),
    position smallint not null,
    source_code text not null,
    source_name text not null,
    target_code text not null,
    target_name text not null,
    primary key (matrix_id, source_code, target_code),
    unique (matrix_id, position),
    constraint hierarchical_relationship_not_diagonal check (
        source_code <> target_code
    )
);

with criteria(matrix_id, ordinal, code, name) as (
    values
        ('cultural', 1, 'C1', 'Passengers’ environmental knowledge & awareness'),
        ('cultural', 2, 'C2', 'Passengers’ cultural dynamics (values, beliefs, norms, traditions, religion, language)'),
        ('cultural', 3, 'C3', 'Passengers’ perceived environmental performance of the airline’s green actions'),
        ('cultural', 4, 'C4', 'Passengers’ willingness-to-pay (WTP) for green initiatives in the air transport sector (carbon offsets, Sustainable Aviation Fuel (SAF))'),
        ('cultural', 5, 'C5', 'Passengers’ trust in airlines’ green actions (low greenwashing skepticism)'),
        ('cultural', 6, 'C6', 'Passengers’ country of origin (in terms of geographical and regulatory environment)'),
        ('economic', 1, 'E1', 'Origin-country GDP per capita'),
        ('economic', 2, 'E2', 'Revenue Potential from Green Practices (Differentiation, Opportunities)'),
        ('economic', 3, 'E3', 'Investment Risk & Financial Risk'),
        ('economic', 4, 'E4', 'Macro-economic stability / price sensitivity context (inflation, crises, etc.) of Origin Market'),
        ('strategic', 1, 'S1', 'Airline’s strategic flexibility (ability to adapt to environmental uncertainties / reconfigure)'),
        ('strategic', 2, 'S2', 'Airline’s strategic resilience (ability to absorb shocks and continue / bounce back)'),
        ('strategic', 3, 'S3', 'Airline’s resource commitment (willingness to invest long-term in sustainability even with uncertain payback)'),
        ('strategic', 4, 'S4', 'Airline’s carbon offset programme quality and credibility'),
        ('strategic', 5, 'S5', 'Airline’s operational and financial capacity to adopt Sustainable Aviation Fuel (SAF), including access to supply, contracts, infrastructure, operational integration and cost management'),
        ('strategic', 6, 'S6', 'Airline’s effectiveness in communicating sustainability to passengers'),
        ('strategic', 7, 'S7', 'Airline’s commitment to its stakeholders (engagement, accountability, responsiveness)'),
        ('strategic', 8, 'S8', 'Airline’s compliance with global environmental regulations and sustainability policies'),
        ('dimension_level', 1, 'C', 'Consumer-Cultural & Behavioural'),
        ('dimension_level', 2, 'E', 'Economic & Market'),
        ('dimension_level', 3, 'S', 'Airline Strategic & Operational')
), numbered as (
    select
        source.matrix_id,
        row_number() over (
            partition by source.matrix_id
            order by source.ordinal, target.ordinal
        )::smallint as position,
        source.code as source_code,
        source.name as source_name,
        target.code as target_code,
        target.name as target_name
    from criteria source
    join criteria target on target.matrix_id = source.matrix_id
    where source.code <> target.code
)
insert into public.hierarchical_relationships (
    matrix_id,
    position,
    source_code,
    source_name,
    target_code,
    target_name
)
select
    matrix_id,
    position,
    source_code,
    source_name,
    target_code,
    target_name
from numbered
on conflict (matrix_id, source_code, target_code) do update
set position = excluded.position,
    source_name = excluded.source_name,
    target_name = excluded.target_name;

create table if not exists public.hierarchical_responses (
    respondent_id uuid not null,
    expert_code text not null,
    matrix_id text not null,
    source_code text not null,
    source_name text not null,
    target_code text not null,
    target_name text not null,
    linguistic_value text not null,
    tfn_l numeric(4, 2) not null,
    tfn_m numeric(4, 2) not null,
    tfn_u numeric(4, 2) not null,
    responded_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    primary key (respondent_id, matrix_id, source_code, target_code),
    constraint hierarchical_response_session foreign key (respondent_id)
        references public.hierarchical_questionnaires (respondent_id),
    constraint hierarchical_response_relationship foreign key (
        matrix_id, source_code, target_code
    ) references public.hierarchical_relationships (
        matrix_id, source_code, target_code
    ),
    constraint hierarchical_response_not_diagonal check (
        source_code <> target_code
    ),
    constraint exact_hierarchical_tfn_mapping check (
        (linguistic_value = 'VL' and tfn_l = 0.00 and tfn_m = 0.00 and tfn_u = 0.25)
        or (linguistic_value = 'LI' and tfn_l = 0.00 and tfn_m = 0.25 and tfn_u = 0.50)
        or (linguistic_value = 'I'  and tfn_l = 0.25 and tfn_m = 0.50 and tfn_u = 0.75)
        or (linguistic_value = 'HI' and tfn_l = 0.50 and tfn_m = 0.75 and tfn_u = 1.00)
        or (linguistic_value = 'VH' and tfn_l = 0.75 and tfn_m = 1.00 and tfn_u = 1.00)
    )
);

create index if not exists hierarchical_questionnaires_status_idx
    on public.hierarchical_questionnaires (status, completed_at desc);
create index if not exists hierarchical_responses_coverage_idx
    on public.hierarchical_responses (matrix_id, source_code, target_code);
create index if not exists hierarchical_responses_responded_idx
    on public.hierarchical_responses (responded_at desc);

create or replace function public.validate_hierarchical_response()
returns trigger
language plpgsql
set search_path = public
as $$
declare
    session_code text;
    session_status text;
    canonical_source_name text;
    canonical_target_name text;
begin
    select hq.expert_code, hq.status
    into session_code, session_status
    from public.hierarchical_questionnaires hq
    where hq.respondent_id = new.respondent_id;

    if not found then
        raise exception 'No hierarchical questionnaire exists for this respondent.';
    end if;
    if session_code <> new.expert_code then
        raise exception 'Response expert code does not match the questionnaire.';
    end if;
    if session_status = 'completed' then
        raise exception 'Completed questionnaire responses are immutable.';
    end if;

    select hr.source_name, hr.target_name
    into canonical_source_name, canonical_target_name
    from public.hierarchical_relationships hr
    where hr.matrix_id = new.matrix_id
      and hr.source_code = new.source_code
      and hr.target_code = new.target_code;

    if not found then
        raise exception 'Relationship is not part of the hierarchical design.';
    end if;
    if new.source_name <> canonical_source_name
       or new.target_name <> canonical_target_name then
        raise exception 'Response criterion names do not match the design.';
    end if;
    return new;
end;
$$;

drop trigger if exists validate_hierarchical_response_write
    on public.hierarchical_responses;
create trigger validate_hierarchical_response_write
before insert or update on public.hierarchical_responses
for each row execute function public.validate_hierarchical_response();

create or replace function public.start_hierarchical_questionnaire(
    p_respondent_id uuid,
    p_expert_code text
)
returns table (
    respondent_id uuid,
    expert_code text,
    design_version text,
    status text,
    started_at timestamptz,
    completed_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
begin
    if p_expert_code !~ '^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$' then
        raise exception 'Invalid anonymous expert code.';
    end if;

    insert into public.hierarchical_questionnaires (
        respondent_id, expert_code
    ) values (
        p_respondent_id, p_expert_code
    ) on conflict on constraint hierarchical_questionnaires_pkey do nothing;

    if exists (
        select 1
        from public.hierarchical_questionnaires hq
        where hq.respondent_id = p_respondent_id
          and hq.expert_code <> p_expert_code
    ) then
        raise exception 'Anonymous expert code does not match the saved session.';
    end if;

    return query
    select hq.respondent_id, hq.expert_code, hq.design_version, hq.status,
           hq.started_at, hq.completed_at
    from public.hierarchical_questionnaires hq
    where hq.respondent_id = p_respondent_id;
end;
$$;

create or replace function public.complete_hierarchical_questionnaire(
    p_respondent_id uuid
)
returns table (
    respondent_id uuid,
    expert_code text,
    design_version text,
    status text,
    started_at timestamptz,
    completed_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
declare
    questionnaire_row public.hierarchical_questionnaires%rowtype;
    response_count integer;
    completion_time timestamptz;
begin
    select * into questionnaire_row
    from public.hierarchical_questionnaires hq
    where hq.respondent_id = p_respondent_id
    for update;

    if not found then
        raise exception 'Hierarchical questionnaire not found.';
    end if;
    if questionnaire_row.status = 'completed' then
        return query
        select hq.respondent_id, hq.expert_code, hq.design_version, hq.status,
               hq.started_at, hq.completed_at
        from public.hierarchical_questionnaires hq
        where hq.respondent_id = p_respondent_id;
        return;
    end if;

    select count(*) into response_count
    from public.hierarchical_responses hr
    where hr.respondent_id = p_respondent_id;

    if (select count(*) from public.hierarchical_relationships) <> 104
       or response_count <> 104 then
        raise exception
            'The hierarchical questionnaire is incomplete (% of 104 responses).',
            response_count;
    end if;

    completion_time := now();
    update public.hierarchical_responses hr
    set responded_at = completion_time
    where hr.respondent_id = p_respondent_id;

    update public.hierarchical_questionnaires hq
    set status = 'completed', completed_at = completion_time
    where hq.respondent_id = p_respondent_id;

    return query
    select hq.respondent_id, hq.expert_code, hq.design_version, hq.status,
           hq.started_at, hq.completed_at
    from public.hierarchical_questionnaires hq
    where hq.respondent_id = p_respondent_id;
end;
$$;

alter table public.hierarchical_questionnaires enable row level security;
alter table public.hierarchical_relationships enable row level security;
alter table public.hierarchical_responses enable row level security;

revoke all on table public.hierarchical_questionnaires from anon, authenticated;
revoke all on table public.hierarchical_relationships from anon, authenticated;
revoke all on table public.hierarchical_responses from anon, authenticated;
revoke all on function public.start_hierarchical_questionnaire(uuid, text)
    from public, anon, authenticated;
revoke all on function public.complete_hierarchical_questionnaire(uuid)
    from public, anon, authenticated;

grant all on table public.hierarchical_questionnaires to service_role;
grant select on table public.hierarchical_relationships to service_role;
grant all on table public.hierarchical_responses to service_role;
grant execute on function public.start_hierarchical_questionnaire(uuid, text)
    to service_role;
grant execute on function public.complete_hierarchical_questionnaire(uuid)
    to service_role;

comment on table public.hierarchical_questionnaires is
    'Anonymous sessions for the 104-answer hierarchical Fuzzy DEMATEL design.';
comment on table public.hierarchical_relationships is
    'The fixed 30 + 12 + 56 + 6 allowed directed relationships.';
comment on table public.hierarchical_responses is
    'Autosaved five-level judgments for the hierarchical design.';
