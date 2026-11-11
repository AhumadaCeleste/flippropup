-- Flip PropUp · módulo Mercado: señales de vendedor, estado de obra, salidas del mercado y foto diaria por barrio (11/11/2026)
-- Pegar en Supabase → SQL Editor → Run. Se puede correr más de una vez.

-- ---------- Señales por aviso ----------
alter table publicaciones add column if not exists fecha_baja timestamptz;      -- cuándo dejó de estar publicado
alter table publicaciones add column if not exists bajas_n integer;             -- cuántas veces bajó de precio
alter table publicaciones add column if not exists baja_total_pct numeric;      -- 0,12 = hoy está 12 % debajo de su precio más alto
alter table publicaciones add column if not exists precio_maximo numeric;       -- precio más alto que tuvo (misma moneda)
alter table publicaciones add column if not exists ultima_baja timestamptz;     -- fecha de la última baja de precio
alter table publicaciones add column if not exists estado_obra text;            -- 'a reciclar' | 'listo' (según el texto del aviso)
create index if not exists publicaciones_ultima_baja_idx on publicaciones (ultima_baja desc nulls last);
create index if not exists publicaciones_estado_obra_idx on publicaciones (estado_obra);

create or replace function calcular_senales() returns integer
language plpgsql security definer set search_path = public as $$
declare n integer;
begin
  with h as (
    select hp.publicacion_id, hp.precio, hp.fecha,
           lag(hp.precio) over (partition by hp.publicacion_id order by hp.fecha) as anterior
    from historial_precios hp
    join publicaciones p on p.id = hp.publicacion_id and p.moneda = hp.moneda and p.estado = 'activo'
  ),
  s as (
    select publicacion_id,
           count(*) filter (where anterior is not null and precio < anterior) as bajas,
           max(fecha) filter (where anterior is not null and precio < anterior) as ultima,
           max(precio) as maximo
    from h group by 1
  )
  update publicaciones p set
    bajas_n = coalesce(s.bajas, 0),
    ultima_baja = s.ultima,
    precio_maximo = s.maximo,
    baja_total_pct = case when s.maximo > p.precio then round((1 - p.precio / s.maximo)::numeric, 4) else 0 end
  from s where s.publicacion_id = p.id;

  update publicaciones set estado_obra = case
      when (coalesce(titulo, '') || ' ' || coalesce(descripcion, '')) ~* '(a reciclar|para reciclar|a refaccionar|para refaccionar|necesita (arreglos|refacci)|a remodelar|para remodelar|a restaurar|a terminar|para actualizar)'
        then 'a reciclar'
      when (coalesce(titulo, '') || ' ' || coalesce(descripcion, '')) ~* '(reciclad[oa]|refaccionad[oa]|a estrenar|impecable|excelente estado|totalmente renovad|remodelad[oa]|como nuev)'
        then 'listo'
    end
  where estado = 'activo';
  get diagnostics n = row_count;
  return n;
end;
$$;
revoke all on function calcular_senales() from public, anon, authenticated;

-- Avisos que dejaron de aparecer en portales que el robot recorre completos (La Voz, webs de inmobiliarias).
create or replace function marcar_salidas(portales text[], dias integer) returns integer
language plpgsql security definer set search_path = public as $$
declare n integer;
begin
  update publicaciones set estado = 'dado_de_baja', fecha_baja = now()
  where estado = 'activo' and portal = any(portales) and ultima_vez < now() - make_interval(days => dias);
  get diagnostics n = row_count;
  return n;
end;
$$;
revoke all on function marcar_salidas(text[], integer) from public, anon, authenticated;

-- ---------- Foto diaria del mercado por barrio (para tendencias) ----------
create table if not exists mercado_diario (
  fecha              date not null,
  tipo               text not null,
  barrio_id          integer not null,     -- 0 = toda la ciudad
  zona               text,
  activos            integer,
  nuevos_7d          integer,
  bajaron_7d         integer,              -- avisos activos que bajaron de precio en los últimos 7 días
  con_bajas          integer,              -- avisos activos que bajaron alguna vez
  mediana_m2         numeric,              -- U$S/m²
  p25_m2             numeric,              -- el 25 % más barato está por debajo de este valor
  m2_reciclar        numeric,              -- mediana U$S/m² de los avisos "a reciclar"
  n_reciclar         integer,
  m2_listo           numeric,              -- mediana U$S/m² de los refaccionados / a estrenar
  n_listo            integer,
  dias_publicado     integer,              -- mediana de días publicado de los activos
  salidas_30d        integer,              -- avisos que dejaron de publicarse en los últimos 30 días
  vida_salidas       integer,              -- mediana de días que estuvieron publicados los que salieron
  descuento_salida   numeric,              -- mediana de cuánto habían bajado antes de salir (0,08 = 8 %)
  primary key (fecha, tipo, barrio_id)
);
alter table mercado_diario enable row level security;
drop policy if exists solo_habilitados on mercado_diario;
create policy solo_habilitados on mercado_diario for select to authenticated using (es_habilitado());

create or replace function registrar_mercado() returns integer
language plpgsql security definer set search_path = public as $$
declare n integer;
begin
  with activos as (
    select tipo, coalesce(barrio_id, 0) as barrio_id, zona, primera_vez, ultima_baja, bajas_n, estado_obra, publicado_desde,
           case when moneda = 'USD' and precio_m2 between 100 and 10000 then precio_m2::numeric end as m2
    from publicaciones
    where estado = 'activo' and barrio_id is not null and tipo is not null
  ),
  a as (
    select tipo, case when grouping(barrio_id) = 1 then 0 else barrio_id end as barrio_id,
           case when grouping(barrio_id) = 1 then 'ciudad' else max(zona) end as zona,
           count(*) as activos,
           count(*) filter (where primera_vez >= now() - interval '7 days') as nuevos_7d,
           count(*) filter (where ultima_baja >= now() - interval '7 days') as bajaron_7d,
           count(*) filter (where bajas_n > 0) as con_bajas,
           percentile_cont(0.5) within group (order by m2) as mediana_m2,
           percentile_cont(0.25) within group (order by m2) as p25_m2,
           percentile_cont(0.5) within group (order by m2) filter (where estado_obra = 'a reciclar') as m2_reciclar,
           count(m2) filter (where estado_obra = 'a reciclar') as n_reciclar,
           percentile_cont(0.5) within group (order by m2) filter (where estado_obra = 'listo') as m2_listo,
           count(m2) filter (where estado_obra = 'listo') as n_listo,
           percentile_cont(0.5) within group (order by (current_date - publicado_desde)) as dias_publicado
    from activos
    group by grouping sets ((tipo, barrio_id), (tipo))
  ),
  salidas as (
    select tipo, case when grouping(barrio_id) = 1 then 0 else barrio_id end as barrio_id,
           count(*) as salidas_30d,
           percentile_cont(0.5) within group (order by (fecha_baja::date - publicado_desde)) as vida,
           percentile_cont(0.5) within group (order by coalesce(baja_total_pct, 0)) as descuento
    from publicaciones
    where estado = 'dado_de_baja' and fecha_baja >= now() - interval '30 days' and barrio_id is not null and tipo is not null
    group by grouping sets ((tipo, barrio_id), (tipo))
  )
  insert into mercado_diario (fecha, tipo, barrio_id, zona, activos, nuevos_7d, bajaron_7d, con_bajas, mediana_m2, p25_m2,
                              m2_reciclar, n_reciclar, m2_listo, n_listo, dias_publicado, salidas_30d, vida_salidas, descuento_salida)
  select current_date, a.tipo, a.barrio_id, a.zona, a.activos, a.nuevos_7d, a.bajaron_7d, a.con_bajas,
         round(a.mediana_m2), round(a.p25_m2), round(a.m2_reciclar), a.n_reciclar, round(a.m2_listo), a.n_listo,
         round(a.dias_publicado), coalesce(s.salidas_30d, 0), round(s.vida), round(s.descuento::numeric, 4)
  from a left join salidas s on s.tipo = a.tipo and s.barrio_id = a.barrio_id
  on conflict (fecha, tipo, barrio_id) do update set
    zona = excluded.zona, activos = excluded.activos, nuevos_7d = excluded.nuevos_7d, bajaron_7d = excluded.bajaron_7d,
    con_bajas = excluded.con_bajas, mediana_m2 = excluded.mediana_m2, p25_m2 = excluded.p25_m2,
    m2_reciclar = excluded.m2_reciclar, n_reciclar = excluded.n_reciclar, m2_listo = excluded.m2_listo, n_listo = excluded.n_listo,
    dias_publicado = excluded.dias_publicado, salidas_30d = excluded.salidas_30d, vida_salidas = excluded.vida_salidas,
    descuento_salida = excluded.descuento_salida;
  get diagnostics n = row_count;
  return n;
end;
$$;
revoke all on function registrar_mercado() from public, anon, authenticated;

-- Inmobiliarias con más avisos en un tipo y zona (para la web).
create or replace function ranking_anunciantes(p_tipo text, p_zona text default null)
returns table (anunciante text, avisos bigint, con_bajas bigint, desvio_mediano numeric, repetidos bigint)
language sql stable security invoker set search_path = public as $$
  select coalesce(nullif(trim(vendedor_nombre), ''), 'Sin nombre') as anunciante,
         count(*) as avisos,
         count(*) filter (where bajas_n > 0) as con_bajas,
         round((percentile_cont(0.5) within group (order by desvio_ref))::numeric, 3) as desvio_mediano,
         count(*) filter (where grupo_n > 1) as repetidos
  from publicaciones
  where estado = 'activo' and tipo = p_tipo and barrio_id is not null
    and (p_zona is null or zona = p_zona)
    and coalesce(vendedor_tipo, '') <> 'Particular' and vendedor_nombre is not null
  group by 1
  having count(*) >= 3
  order by 2 desc
  limit 15;
$$;
grant execute on function ranking_anunciantes(text, text) to authenticated;

select calcular_senales();
select registrar_mercado();
