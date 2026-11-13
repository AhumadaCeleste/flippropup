-- Flip PropUp · Zonaprop (13/11/2026)
-- Zonaprop bloquea a los servidores de GitHub (Cloudflare). Los avisos se leen desde el navegador
-- de Cele con una tarea programada y se dejan en zonaprop_crudo; el robot diario los procesa.
-- El m² de Zonaprop por barrio pasa a ser la referencia de precio de todos los avisos.

-- ---------- Recepción de lo capturado en el navegador ----------
create table if not exists zonaprop_crudo (
  id      bigserial primary key,
  lote    text not null,           -- un lote por captura (fecha y hora)
  tipo    text not null,           -- departamento / casa / terreno
  pagina  integer not null,
  paginas integer not null,        -- páginas que informa Zonaprop para ese tipo
  filas   jsonb not null,
  creado  timestamptz not null default now(),
  unique (lote, tipo, pagina)
);
alter table zonaprop_crudo enable row level security;   -- sin políticas: solo el robot (service_role)

-- Claves internas (no se leen desde la web).
create table if not exists config_privada (clave text primary key, valor text not null);
alter table config_privada enable row level security;

-- La captura llama a esta función con la clave anon de la web + una clave propia de Zonaprop.
create or replace function zonaprop_cargar(clave text, lote text, tipo text, pagina integer, paginas integer, filas jsonb)
returns integer language plpgsql security definer set search_path = public as $$
begin
  if clave is null or clave <> (select valor from config_privada where config_privada.clave = 'zonaprop') then
    raise exception 'clave incorrecta';
  end if;
  if tipo not in ('departamento', 'casa', 'terreno') or jsonb_typeof(filas) <> 'array' or jsonb_array_length(filas) > 100 then
    raise exception 'datos inválidos';
  end if;
  delete from zonaprop_crudo where creado < now() - interval '4 days';
  insert into zonaprop_crudo (lote, tipo, pagina, paginas, filas)
  values (lote, tipo, pagina, paginas, filas)
  on conflict on constraint zonaprop_crudo_lote_tipo_pagina_key do update set filas = excluded.filas, paginas = excluded.paginas;
  return jsonb_array_length(filas);
end;
$$;
revoke all on function zonaprop_cargar(text, text, text, integer, integer, jsonb) from public;
grant execute on function zonaprop_cargar(text, text, text, integer, integer, jsonb) to anon, authenticated;

-- ---------- m² de Zonaprop por barrio ----------
alter table publicaciones add column if not exists zp_m2 numeric;     -- mediana U$S/m² de Zonaprop (mismo tipo y barrio)
alter table publicaciones add column if not exists zp_n integer;      -- cuántos avisos de Zonaprop hay detrás
alter table publicaciones add column if not exists zp_nivel text;     -- barrio / zona / ciudad

create or replace function recalcular_referencias() returns integer
language plpgsql security definer set search_path = public as $$
declare n integer;
begin
  with base as (
    select id, portal, tipo, barrio_id, zona, coalesce(dormitorios, '') as dorm, precio_m2::numeric as v
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
  -- Zonaprop: mediana del m² de sus avisos por tipo y barrio (si hay pocos, por zona; si no, ciudad)
  z1 as (select tipo, barrio_id, percentile_cont(0.5) within group (order by v) as m, count(*) as c
         from base where portal = 'zonaprop' and barrio_id is not null group by 1, 2 having count(*) >= 4),
  z2 as (select tipo, zona, percentile_cont(0.5) within group (order by v) as m, count(*) as c
         from base where portal = 'zonaprop' and zona is not null group by 1, 2 having count(*) >= 8),
  z3 as (select tipo, percentile_cont(0.5) within group (order by v) as m, count(*) as c
         from base where portal = 'zonaprop' group by 1 having count(*) >= 10),
  calc as (
    select p.id,
           coalesce(g1.m, g2.m, g3.m, g4.m) as ref,
           coalesce(g1.c, g2.c, g3.c, g4.c) as cuantos,
           case when g1.m is not null then 'barrio' when g2.m is not null then 'zona'
                when g3.m is not null then 'ciudad' when g4.m is not null then 'tipo' end as nivel,
           coalesce(z1.m, z2.m, z3.m) as zp,
           coalesce(z1.c, z2.c, z3.c) as zp_c,
           case when z1.m is not null then 'barrio' when z2.m is not null then 'zona'
                when z3.m is not null then 'ciudad' end as zp_niv
    from publicaciones p
    left join g1 on g1.tipo = p.tipo and g1.barrio_id = p.barrio_id and g1.dorm = coalesce(p.dormitorios, '')
    left join g2 on g2.tipo = p.tipo and g2.zona = p.zona and g2.dorm = coalesce(p.dormitorios, '')
    left join g3 on g3.tipo = p.tipo and g3.dorm = coalesce(p.dormitorios, '')
    left join g4 on g4.tipo = p.tipo
    left join z1 on z1.tipo = p.tipo and z1.barrio_id = p.barrio_id
    left join z2 on z2.tipo = p.tipo and z2.zona = p.zona
    left join z3 on z3.tipo = p.tipo
    where p.estado = 'activo'
  ),
  -- referencia para el desvío y el puntaje: el m² de Zonaprop del barrio o la zona; si no hay, el de todos los portales
  usar as (select id, ref, cuantos, nivel, zp, zp_c, zp_niv,
                  case when zp_niv in ('barrio', 'zona') then zp else ref end as r
           from calc),
  maximos as (select publicacion_id, max(precio) as maximo from historial_precios group by 1)
  update publicaciones p set
    ref_m2 = case when p.moneda = 'USD' then round(u.ref) end,
    ref_n = case when p.moneda = 'USD' then u.cuantos end,
    ref_nivel = case when p.moneda = 'USD' then u.nivel end,
    zp_m2 = case when p.moneda = 'USD' then round(u.zp) end,
    zp_n = case when p.moneda = 'USD' then u.zp_c end,
    zp_nivel = case when p.moneda = 'USD' then u.zp_niv end,
    desvio_ref = case when p.moneda = 'USD' and p.precio_m2 between 100 and 10000 and u.r > 0
                      then round((p.precio_m2 / u.r - 1)::numeric, 4) end,
    puntaje = least(100, greatest(0, round(
        coalesce(case when p.moneda = 'USD' and p.precio_m2 between 100 and 10000 and u.r > 0
             then greatest(0, least(1, (1.15 - p.precio_m2 / u.r) / 0.45)) * 50 end, 0)
      + least(1, greatest(0, current_date - coalesce(p.publicado_desde, current_date)) / 180.0) * 15
      + coalesce(least(1, greatest(0, (mx.maximo - p.precio) / nullif(mx.maximo, 0)) / 0.15) * 20, 0)
      + case when (coalesce(p.titulo, '') || ' ' || coalesce(p.descripcion, ''))
                  ~* '(reciclar|refaccionar|a refaccionar|oportunidad|sucesi[oó]n|urgente|due[ñn]o (vende|directo)|apurad|escucha ofertas|liquido)'
             then 15 else 0 end
    )))::integer
  from usar u left join maximos mx on mx.publicacion_id = u.id
  where p.id = u.id;
  get diagnostics n = row_count;
  return n;
end;
$$;
revoke all on function recalcular_referencias() from public, anon, authenticated;
alter function recalcular_referencias() set statement_timeout = '180s';
