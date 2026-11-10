-- Flip PropUp · barrios oficiales, zonas, antigüedad, índice IDECOR, referencia de mercado y puntaje (10/11/2026)
-- Pegar en Supabase → SQL Editor → Run. Se puede correr más de una vez.

-- ---------- Barrios oficiales de la ciudad de Córdoba (Municipalidad) ----------
create table if not exists barrios (
  id       integer primary key,   -- RelOID del catastro municipal
  nombre   text not null,         -- como figura en el registro (MAYÚSCULAS)
  bonito   text not null,         -- para mostrar
  zona     text not null check (zona in ('centro', 'norte', 'sur', 'este', 'oeste')),
  lat      numeric,
  lng      numeric
);
alter table barrios enable row level security;
drop policy if exists solo_habilitados on barrios;
create policy solo_habilitados on barrios for all to authenticated using (es_habilitado()) with check (es_habilitado());

-- Los 451 barrios los carga el robot desde scraper/datos/barrios-cordoba.geojson en su primera corrida.

-- ---------- Columnas nuevas en publicaciones ----------
alter table publicaciones add column if not exists barrio_id integer;          -- barrios.id (solo ciudad de Córdoba)
alter table publicaciones add column if not exists barrio_origen text;         -- punto | nombre | texto
alter table publicaciones add column if not exists zona text;                  -- centro | norte | sur | este | oeste
alter table publicaciones add column if not exists publicado_desde date;       -- fecha de publicación del portal o, si no la da, cuando lo vimos por primera vez
alter table publicaciones add column if not exists idecor_m2 numeric;          -- U$S/m² de referencia IDECOR (casas: ofertas OMI cercanas; terrenos: valor de la tierra)
alter table publicaciones add column if not exists idecor_n integer;           -- cuántos datos IDECOR hay detrás
alter table publicaciones add column if not exists idecor_base text;           -- 'omi 600 m', 'vut parcela', ...
alter table publicaciones add column if not exists idecor_parcela text;        -- nomenclatura catastral (terrenos)
alter table publicaciones add column if not exists idecor_en timestamptz;
alter table publicaciones add column if not exists ref_m2 numeric;             -- mediana U$S/m² de avisos parecidos
alter table publicaciones add column if not exists ref_n integer;
alter table publicaciones add column if not exists ref_nivel text;             -- barrio | zona | ciudad | tipo
alter table publicaciones add column if not exists puntaje integer;            -- 0 a 100: qué tan buena oportunidad parece

update publicaciones set publicado_desde = coalesce(fecha_publicacion, (primera_vez at time zone 'America/Argentina/Cordoba')::date)
  where publicado_desde is null;

create index if not exists publicaciones_barrio_id_idx on publicaciones (barrio_id);
create index if not exists publicaciones_zona_idx on publicaciones (zona);
create index if not exists publicaciones_publicado_idx on publicaciones (publicado_desde);
create index if not exists publicaciones_puntaje_idx on publicaciones (puntaje desc nulls last);

-- ---------- Búsquedas: la búsqueda base no manda "nuevos" por email ----------
alter table busquedas add column if not exists sin_alertas boolean not null default false;
insert into busquedas (nombre, filtros, activa, creada_por, sin_alertas)
select 'Base · Córdoba capital (todo)',
       '{"tipos": ["casa", "departamento", "terreno"], "provincia_tid": 3173, "ciudad_tid": 3194, "base": true}'::jsonb,
       true, 'robot', true
where not exists (select 1 from busquedas where filtros ->> 'base' = 'true');

-- ---------- Actualización masiva desde el robot ----------
create or replace function actualizar_publicaciones(filas jsonb) returns integer
language plpgsql security definer set search_path = public as $$
declare n integer;
begin
  update publicaciones p set
    barrio_id      = case when x ? 'barrio_id' then (x->>'barrio_id')::integer else p.barrio_id end,
    barrio_origen  = case when x ? 'barrio_origen' then x->>'barrio_origen' else p.barrio_origen end,
    zona           = case when x ? 'zona' then x->>'zona' else p.zona end,
    idecor_m2      = case when x ? 'idecor_m2' then (x->>'idecor_m2')::numeric else p.idecor_m2 end,
    idecor_n       = case when x ? 'idecor_n' then (x->>'idecor_n')::integer else p.idecor_n end,
    idecor_base    = case when x ? 'idecor_base' then x->>'idecor_base' else p.idecor_base end,
    idecor_parcela = case when x ? 'idecor_parcela' then x->>'idecor_parcela' else p.idecor_parcela end,
    idecor_en      = case when x ? 'idecor_m2' or x ? 'idecor_en' then now() else p.idecor_en end
  from jsonb_array_elements(filas) x
  where p.id = (x->>'id')::bigint;
  get diagnostics n = row_count;
  return n;
end;
$$;
revoke all on function actualizar_publicaciones(jsonb) from public, anon, authenticated;

-- Referencia de mercado (mediana U$S/m² de avisos activos parecidos) y puntaje de oportunidad.
create or replace function recalcular_referencias() returns integer
language plpgsql security definer set search_path = public as $$
declare n integer;
begin
  with base as (
    select id, tipo, barrio_id, zona, coalesce(dormitorios, '') as dorm, precio_m2::numeric as v
    from publicaciones
    where estado = 'activo' and moneda = 'USD' and tipo is not null and precio_m2 between 100 and 10000
  ),
  g1 as (select tipo, barrio_id, dorm, percentile_cont(0.5) within group (order by v) as m, count(*) as c
         from base where barrio_id is not null group by 1, 2, 3 having count(*) >= 5),
  g2 as (select tipo, zona, dorm, percentile_cont(0.5) within group (order by v) as m, count(*) as c
         from base where zona is not null group by 1, 2, 3 having count(*) >= 8),
  g3 as (select tipo, dorm, percentile_cont(0.5) within group (order by v) as m, count(*) as c
         from base group by 1, 2 having count(*) >= 10),
  g4 as (select tipo, percentile_cont(0.5) within group (order by v) as m, count(*) as c
         from base group by 1 having count(*) >= 10),
  calc as (
    select p.id,
           coalesce(g1.m, g2.m, g3.m, g4.m) as ref,
           coalesce(g1.c, g2.c, g3.c, g4.c) as cuantos,
           case when g1.m is not null then 'barrio' when g2.m is not null then 'zona'
                when g3.m is not null then 'ciudad' when g4.m is not null then 'tipo' end as nivel
    from publicaciones p
    left join g1 on g1.tipo = p.tipo and g1.barrio_id = p.barrio_id and g1.dorm = coalesce(p.dormitorios, '')
    left join g2 on g2.tipo = p.tipo and g2.zona = p.zona and g2.dorm = coalesce(p.dormitorios, '')
    left join g3 on g3.tipo = p.tipo and g3.dorm = coalesce(p.dormitorios, '')
    left join g4 on g4.tipo = p.tipo
    where p.estado = 'activo'
  ),
  maximos as (select publicacion_id, max(precio) as maximo from historial_precios group by 1)
  update publicaciones p set
    ref_m2 = case when p.moneda = 'USD' then round(calc.ref) end,
    ref_n = case when p.moneda = 'USD' then calc.cuantos end,
    ref_nivel = case when p.moneda = 'USD' then calc.nivel end,
    puntaje = least(100, greatest(0, round(
        -- precio por m² contra la referencia (hasta 50): 15 % o más abajo suma; 15 % arriba no suma
        coalesce(case when p.moneda = 'USD' and p.precio_m2 > 0 and calc.ref > 0
             then greatest(0, least(1, (1.15 - p.precio_m2 / calc.ref) / 0.45)) * 50 end, 0)
        -- días publicado (hasta 15): a los 180 días suma todo
      + least(1, greatest(0, current_date - coalesce(p.publicado_desde, current_date)) / 180.0) * 15
        -- bajas de precio acumuladas desde el máximo (hasta 20): 15 % o más suma todo
      + coalesce(least(1, greatest(0, (mx.maximo - p.precio) / nullif(mx.maximo, 0)) / 0.15) * 20, 0)
        -- palabras que suelen marcar urgencia o potencial (15)
      + case when (coalesce(p.titulo, '') || ' ' || coalesce(p.descripcion, ''))
                  ~* '(reciclar|refaccionar|a refaccionar|oportunidad|sucesi[oó]n|urgente|due[ñn]o (vende|directo)|apurad|escucha ofertas|liquido)'
             then 15 else 0 end
    )))::integer
  from calc left join maximos mx on mx.publicacion_id = calc.id
  where p.id = calc.id;
  get diagnostics n = row_count;
  return n;
end;
$$;
revoke all on function recalcular_referencias() from public, anon, authenticated;
