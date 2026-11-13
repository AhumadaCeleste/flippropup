-- Flip PropUp · velocidad de la web (13/11/2026)

-- 1) Reglas de seguridad: "(select es_habilitado())" se calcula una vez por consulta.
--    Escrito como "es_habilitado()" Postgres lo repetía en cada fila (40.000 avisos = 40.000 veces).
do $$
declare t text;
begin
  foreach t in array array['ubicaciones','busquedas','publicaciones','historial_precios','busqueda_resultados',
    'seguimientos','notas','descartes','alertas','ejecuciones','relevamientos','barrios']
  loop
    execute format('drop policy if exists solo_habilitados on %I', t);
    execute format('create policy solo_habilitados on %I for all to authenticated using ((select es_habilitado())) with check ((select es_habilitado()))', t);
  end loop;
end $$;
drop policy if exists solo_lectura on usuarios_habilitados;
create policy solo_lectura on usuarios_habilitados for select to authenticated using ((select es_habilitado()));
drop policy if exists solo_habilitados on mercado_diario;
create policy solo_habilitados on mercado_diario for select to authenticated using ((select es_habilitado()));

-- 2) Índices para lo que más se consulta: Buscar pide cada portal por separado, solo activos.
create index if not exists publicaciones_portal_activos_idx on publicaciones (portal, primera_vez desc) where estado = 'activo';
create index if not exists publicaciones_portal_puntaje_idx on publicaciones (portal, puntaje desc nulls last) where estado = 'activo';
create index if not exists publicaciones_portal_precio_idx on publicaciones (portal, precio) where estado = 'activo';
create index if not exists publicaciones_tipo_activos_idx on publicaciones (tipo, barrio_id) where estado = 'activo';
create index if not exists alertas_pub_idx on alertas (publicacion_id);
create index if not exists busqueda_resultados_pub_idx on busqueda_resultados (publicacion_id);
create index if not exists ubicaciones_portal_nombre_idx on ubicaciones (portal, nombre);

analyze publicaciones;
