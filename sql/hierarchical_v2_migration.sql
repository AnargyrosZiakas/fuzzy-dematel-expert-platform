-- Upgrade the hierarchical questionnaire from v1 (104 answers) to v2 (90).
--
-- v2 removes the former stakeholder-commitment S7 criterion and renumbers the
-- former environmental-compliance S8 criterion as S7. Existing non-strategic
-- progress is preserved. The transaction refuses to proceed if completed v1
-- questionnaires or answers involving the former S7/S8 criteria exist, because
-- those records require a deliberate research archive rather than silent edits.

begin;

lock table public.hierarchical_questionnaires in share row exclusive mode;
lock table public.hierarchical_responses in share row exclusive mode;
lock table public.hierarchical_relationships in share row exclusive mode;

do $$
begin
    if exists (
        select 1
        from public.hierarchical_questionnaires
        where design_version = 'hierarchical_v1'
          and status = 'completed'
    ) then
        raise exception
            'Cannot automatically upgrade completed hierarchical_v1 questionnaires.';
    end if;

    if exists (
        select 1
        from public.hierarchical_responses
        where matrix_id = 'strategic'
          and (
              source_code = 'S8'
              or target_code = 'S8'
              or source_name = 'Airline’s commitment to its stakeholders (engagement, accountability, responsiveness)'
              or target_name = 'Airline’s commitment to its stakeholders (engagement, accountability, responsiveness)'
          )
    ) then
        raise exception
            'Cannot automatically remap existing strategic S7/S8 answers.';
    end if;
end;
$$;

alter table public.hierarchical_questionnaires
    drop constraint if exists hierarchical_questionnaires_design_version_check;
alter table public.hierarchical_questionnaires
    drop constraint if exists hierarchical_design_version_check;

update public.hierarchical_questionnaires
set design_version = 'hierarchical_v2'
where design_version = 'hierarchical_v1';

alter table public.hierarchical_questionnaires
    alter column design_version set default 'hierarchical_v2';
alter table public.hierarchical_questionnaires
    add constraint hierarchical_design_version_check
    check (design_version = 'hierarchical_v2');

delete from public.hierarchical_relationships
where matrix_id = 'strategic'
  and (
      source_code = 'S8'
      or target_code = 'S8'
      or source_name = 'Airline’s commitment to its stakeholders (engagement, accountability, responsiveness)'
      or target_name = 'Airline’s commitment to its stakeholders (engagement, accountability, responsiveness)'
  );

update public.hierarchical_relationships
set position = position + 100
where matrix_id = 'strategic';

with criteria(ordinal, code, name) as (
    values
        (1, 'S1', 'Airline’s strategic flexibility (ability to adapt to environmental uncertainties / reconfigure)'),
        (2, 'S2', 'Airline’s strategic resilience (ability to absorb shocks and continue / bounce back)'),
        (3, 'S3', 'Airline’s resource commitment (willingness to invest long-term in sustainability even with uncertain payback)'),
        (4, 'S4', 'Airline’s carbon offset programme quality and credibility'),
        (5, 'S5', 'Airline’s operational and financial capacity to adopt Sustainable Aviation Fuel (SAF), including access to supply, contracts, infrastructure, operational integration and cost management'),
        (6, 'S6', 'Airline’s effectiveness in communicating sustainability to passengers'),
        (7, 'S7', 'Airline’s compliance with global environmental regulations and sustainability policies')
), numbered as (
    select
        row_number() over (order by source.ordinal, target.ordinal)::smallint
            as position,
        source.code as source_code,
        source.name as source_name,
        target.code as target_code,
        target.name as target_name
    from criteria source
    cross join criteria target
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
    'strategic',
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

    if (select count(*) from public.hierarchical_relationships) <> 90
       or response_count <> 90 then
        raise exception
            'The hierarchical questionnaire is incomplete (% of 90 responses).',
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

comment on table public.hierarchical_questionnaires is
    'Anonymous sessions for the 90-answer hierarchical Fuzzy DEMATEL v2 design.';
comment on table public.hierarchical_relationships is
    'The fixed 30 + 12 + 42 + 6 allowed directed relationships.';

do $$
begin
    if (select count(*) from public.hierarchical_relationships) <> 90 then
        raise exception 'Expected exactly 90 hierarchical relationships.';
    end if;
    if (
        select count(*)
        from public.hierarchical_relationships
        where matrix_id = 'strategic'
    ) <> 42 then
        raise exception 'Expected exactly 42 strategic relationships.';
    end if;
    if exists (
        select 1
        from public.hierarchical_relationships
        where matrix_id = 'strategic'
          and (source_code = 'S8' or target_code = 'S8')
    ) then
        raise exception 'S8 must not exist in the hierarchical v2 design.';
    end if;
end;
$$;

commit;
