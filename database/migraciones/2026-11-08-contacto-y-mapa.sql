-- Flip PropUp · teléfono del anunciante y control de fichas ya revisadas (08/11/2026)
-- Pegar en Supabase → SQL Editor → Run. Se puede correr más de una vez sin problema.
alter table publicaciones add column if not exists telefono text;          -- solo dígitos, formato 549 + área + número
alter table publicaciones add column if not exists enriquecido_en timestamptz; -- cuándo el robot leyó la ficha (ubicación y teléfono)
create index if not exists publicaciones_coordenadas_idx on publicaciones (lat, lng) where lat is not null;
