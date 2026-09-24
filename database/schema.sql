-- ============================================================
-- Flip PropUp · Base de datos (Supabase / PostgreSQL)
-- Pegá TODO este archivo en Supabase > SQL Editor > New query > Run.
-- Se puede volver a ejecutar sin romper nada.
-- ============================================================

-- ---------- Usuarios habilitados (lista blanca) ----------
create table if not exists usuarios_habilitados (
  email      text primary key,
  nombre     text,
  creado     timestamptz not null default now()
);

insert into usuarios_habilitados (email, nombre) values
  ('ahumadamariaceleste@gmail.com', 'Cele'),
  ('diegohsuarez@gmail.com', 'Diego')
on conflict (email) do nothing;

-- ¿El usuario que hace la consulta está en la lista?
create or replace function es_habilitado() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from usuarios_habilitados
    where lower(email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );
$$;

-- Bloquea el alta en Supabase Auth de cualquier email que no esté en la lista.
create or replace function bloquear_no_habilitados() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if not exists (select 1 from usuarios_habilitados where lower(email) = lower(new.email)) then
    raise exception 'El email % no está habilitado para Flip PropUp', new.email;
  end if;
  return new;
end;
$$;

drop trigger if exists solo_habilitados on auth.users;
create trigger solo_habilitados before insert on auth.users
  for each row execute function bloquear_no_habilitados();

-- ---------- Ubicaciones de cada portal (para los desplegables) ----------
create table if not exists ubicaciones (
  portal     text not null default 'lavoz',
  tid        integer not null,
  nombre     text not null,
  tipo       text not null check (tipo in ('provincia', 'ciudad', 'barrio')),
  padre_tid  integer,
  primary key (portal, tid)
);

-- ---------- Búsquedas guardadas ----------
create table if not exists busquedas (
  id                uuid primary key default gen_random_uuid(),
  nombre            text not null,
  filtros           jsonb not null,
  activa            boolean not null default true,
  creada_por        text,
  creada            timestamptz not null default now(),
  ultima_ejecucion  timestamptz
);

-- ---------- Publicaciones (un aviso por fila, sin duplicados) ----------
create table if not exists publicaciones (
  id                  bigserial primary key,
  portal              text not null,
  portal_id           text not null,
  url                 text not null,
  titulo              text,
  descripcion         text,
  tipo                text,            -- casa | departamento | terreno
  operacion           text default 'venta',
  provincia           text,
  ciudad              text,
  barrio              text,
  lat                 numeric,
  lng                 numeric,
  precio              numeric,
  moneda              text,            -- USD | ARS
  superficie_total    numeric,
  dormitorios         text,
  banos               text,
  vendedor_tipo       text,            -- Particular | Inmobiliaria | ...
  vendedor_nombre     text,
  apto_escritura      text,
  apto_credito        text,
  fotos               jsonb not null default '[]'::jsonb,
  foto_principal      text,
  fecha_publicacion   date,
  primera_vez         timestamptz not null default now(),
  ultima_vez          timestamptz not null default now(),
  estado              text not null default 'activo' check (estado in ('activo', 'dado_de_baja')),
  precio_m2           numeric generated always as (
                        case when superficie_total > 0 and precio is not null
                             then round(precio / superficie_total) end
                      ) stored,
  unique (portal, portal_id)
);
create index if not exists publicaciones_barrio_idx on publicaciones (ciudad, barrio);
create index if not exists publicaciones_precio_idx on publicaciones (moneda, precio);

create table if not exists historial_precios (
  id              bigserial primary key,
  publicacion_id  bigint not null references publicaciones(id) on delete cascade,
  precio          numeric,
  moneda          text,
  fecha           timestamptz not null default now()
);
create index if not exists historial_pub_idx on historial_precios (publicacion_id, fecha);

-- Qué publicaciones encontró cada búsqueda guardada
create table if not exists busqueda_resultados (
  busqueda_id     uuid   not null references busquedas(id) on delete cascade,
  publicacion_id  bigint not null references publicaciones(id) on delete cascade,
  primera_vez     timestamptz not null default now(),
  primary key (busqueda_id, publicacion_id)
);

-- ---------- Seguimiento (compartido entre los usuarios) ----------
create table if not exists seguimientos (
  publicacion_id   bigint primary key references publicaciones(id) on delete cascade,
  estado           text not null default 'Interesa'
                   check (estado in ('Interesa', 'Contactado', 'Visitado', 'Ofertado', 'Descartado', 'Comprado')),
  precio_inicial   numeric,
  precio_objetivo  numeric,
  agregado_por     text,
  agregado         timestamptz not null default now()
);

create table if not exists notas (
  id              bigserial primary key,
  publicacion_id  bigint not null references publicaciones(id) on delete cascade,
  autor           text,
  texto           text not null,
  creada          timestamptz not null default now()
);

create table if not exists descartes (
  publicacion_id  bigint primary key references publicaciones(id) on delete cascade,
  por             text,
  fecha           timestamptz not null default now()
);

-- ---------- Alertas y registro del robot ----------
create table if not exists alertas (
  id              bigserial primary key,
  publicacion_id  bigint not null references publicaciones(id) on delete cascade,
  busqueda_id     uuid references busquedas(id) on delete set null,
  tipo            text not null check (tipo in ('nuevo', 'baja_precio', 'suba_precio', 'dado_de_baja', 'precio_objetivo')),
  valor_anterior  numeric,
  valor_nuevo     numeric,
  fecha           timestamptz not null default now(),
  enviada         boolean not null default false
);

create table if not exists ejecuciones (
  id       bigserial primary key,
  inicio   timestamptz not null default now(),
  fin      timestamptz,
  estado   text,
  detalle  text
);

-- ---------- Seguridad a nivel de fila (RLS) ----------
-- La web solo puede leer/escribir si el usuario está habilitado.
-- El robot usa la clave "service_role", que no pasa por estas reglas.
do $$
declare t text;
begin
  foreach t in array array['usuarios_habilitados','ubicaciones','busquedas','publicaciones',
    'historial_precios','busqueda_resultados','seguimientos','notas','descartes','alertas','ejecuciones']
  loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists solo_habilitados on %I', t);
    execute format('create policy solo_habilitados on %I for all to authenticated using (es_habilitado()) with check (es_habilitado())', t);
  end loop;
end $$;

-- La lista de usuarios solo se lee desde la web (se edita desde Supabase).
drop policy if exists solo_habilitados on usuarios_habilitados;
drop policy if exists solo_lectura on usuarios_habilitados;
create policy solo_lectura on usuarios_habilitados for select to authenticated using (es_habilitado());
