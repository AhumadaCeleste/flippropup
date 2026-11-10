-- Flip PropUp · limpia superficies imposibles y el puntaje no usa precios por m² absurdos (10/11/2026)
update publicaciones set superficie_total = null
  where superficie_total is not null
    and (superficie_total < 12 or (tipo <> 'terreno' and superficie_total > 5000) or superficie_total > 500000);

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
        coalesce(case when p.moneda = 'USD' and p.precio_m2 between 100 and 10000 and calc.ref > 0
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

select recalcular_referencias();
