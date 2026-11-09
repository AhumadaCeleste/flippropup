-- Flip PropUp · teléfono del anunciante y control de fichas ya revisadas (08/11/2026)
-- Pegar en Supabase → SQL Editor → Run. Se puede correr más de una vez sin problema.
alter table publicaciones add column if not exists telefono text;          -- solo dígitos, formato 549 + área + número
alter table publicaciones add column if not exists enriquecido_en timestamptz; -- cuándo el robot leyó la ficha (ubicación y teléfono)
create index if not exists publicaciones_coordenadas_idx on publicaciones (lat, lng) where lat is not null;

-- ---------- Relevamientos en la calle (foto + ubicación + teléfono del cartel) ----------
create table if not exists relevamientos (
  id          bigserial primary key,
  creado      timestamptz not null default now(),
  creado_por  text,
  lat         numeric,
  lng         numeric,
  direccion   text,
  telefono    text,            -- leído del cartel (549 + área + número)
  nota        text,
  foto_path   text,            -- ruta en el bucket "relevamientos" de Supabase Storage
  activo      boolean not null default true   -- true = avisar si aparece un aviso cerca o con ese teléfono
);
alter table relevamientos enable row level security;
drop policy if exists solo_habilitados on relevamientos;
create policy solo_habilitados on relevamientos for all to authenticated using (es_habilitado()) with check (es_habilitado());

alter table alertas add column if not exists relevamiento_id bigint references relevamientos(id) on delete cascade;
alter table alertas drop constraint if exists alertas_tipo_check;
alter table alertas add constraint alertas_tipo_check
  check (tipo in ('nuevo', 'baja_precio', 'suba_precio', 'dado_de_baja', 'precio_objetivo', 'cerca_relevamiento'));

-- Fotos de los relevamientos (privadas: solo usuarios habilitados)
insert into storage.buckets (id, name, public) values ('relevamientos', 'relevamientos', false)
  on conflict (id) do nothing;
drop policy if exists relevamientos_fotos on storage.objects;
create policy relevamientos_fotos on storage.objects for all to authenticated
  using (bucket_id = 'relevamientos' and es_habilitado())
  with check (bucket_id = 'relevamientos' and es_habilitado());
