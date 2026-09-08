create extension if not exists pgcrypto;

create table if not exists cliente (
  id uuid primary key default gen_random_uuid(),
  nombre text not null,
  servicio text not null,
  linea_base_puntos numeric(10,1) not null check (linea_base_puntos >= 0),
  activo boolean not null default true
);

create table if not exists usuario (
  id uuid primary key,
  nombre text not null,
  rol text not null check (rol in ('cliente', 'lider', 'equipo_delivery')),
  cliente_id uuid references cliente(id),
  activo boolean not null default true
);

create table if not exists matriz_sizing (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references cliente(id),
  version integer not null check (version > 0),
  criterios jsonb not null,
  umbrales jsonb not null,
  vigente_desde timestamptz not null default now(),
  creada_por text not null,
  unique (cliente_id, version)
);

create table if not exists historia_usuario (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references cliente(id),
  texto_original text not null,
  texto_ocr text,
  contiene_contenido_ocr boolean not null default false,
  imagenes_urls jsonb,
  estado text not null check (
    estado in (
      'BORRADOR',
      'EN_ANALISIS_COMPLETITUD',
      'INCOMPLETA',
      'COMPLETA',
      'EN_SIZING',
      'PENDIENTE_REVISION_OCR',
      'SIZING_CALCULADO',
      'PENDIENTE_VALIDACION_LIDER',
      'SIZING_VALIDADO',
      'PENDIENTE_ACEPTACION_CLIENTE',
      'RECHAZADA_POR_CLIENTE',
      'ACEPTADA',
      'EN_EJECUCION',
      'ENTREGADA'
    )
  ),
  resultado_completitud text check (resultado_completitud in ('completa', 'incompleta') or resultado_completitud is null),
  feedback_completitud text,
  sugerencias_mejora jsonb,
  criterios_extraidos jsonb,
  sizing_calculado text,
  puntos_calculados numeric(10,1) check (puntos_calculados is null or puntos_calculados >= 0),
  sizing_validado_por text,
  sizing_validado_en timestamptz,
  aceptada_por_cliente boolean,
  fecha_carga timestamptz not null default now(),
  fecha_entrega timestamptz,
  matriz_sizing_id uuid references matriz_sizing(id)
);

create table if not exists consumo_mensual (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references cliente(id),
  periodo date not null,
  linea_base numeric(10,1) not null check (linea_base >= 0),
  consumido numeric(10,1) not null default 0 check (consumido >= 0),
  unique (cliente_id, periodo),
  check (extract(day from periodo) = 1)
);

create table if not exists log_auditoria (
  id uuid primary key default gen_random_uuid(),
  historia_id uuid references historia_usuario(id),
  evento text not null,
  actor text not null,
  detalle jsonb,
  timestamp timestamptz not null default now()
);

create index if not exists idx_historia_cliente_estado_fecha
  on historia_usuario (cliente_id, estado, fecha_carga desc);

create index if not exists idx_matriz_cliente_vigente
  on matriz_sizing (cliente_id, vigente_desde desc);

create index if not exists idx_consumo_cliente_periodo
  on consumo_mensual (cliente_id, periodo);

create index if not exists idx_auditoria_historia_timestamp
  on log_auditoria (historia_id, timestamp);

alter table cliente enable row level security;
alter table usuario enable row level security;
alter table matriz_sizing enable row level security;
alter table historia_usuario enable row level security;
alter table consumo_mensual enable row level security;
alter table log_auditoria enable row level security;

insert into cliente (id, nombre, servicio, linea_base_puntos, activo)
values (
  '11111111-1111-1111-1111-111111111111',
  'DEMO',
  coalesce(nullif(current_setting('app.demo_servicio', true), ''), 'DEMO'),
  coalesce(nullif(current_setting('app.demo_linea_base_puntos', true), '')::numeric, 100),
  true
)
on conflict (id) do nothing;

insert into matriz_sizing (cliente_id, version, criterios, umbrales, vigente_desde, creada_por)
values (
  '11111111-1111-1111-1111-111111111111',
  1,
  '{
    "complejidad_tecnica": { "baja": 1, "media": 3, "alta": 5 },
    "por_integracion_detectada": 2,
    "por_ambiguedad_detectada": 1,
    "por_dependencia_externa": 2,
    "por_criterio_aceptacion": 0.5
  }'::jsonb,
  '[
    { "tamano": "XS", "puntos_max": 3 },
    { "tamano": "S", "puntos_max": 6 },
    { "tamano": "M", "puntos_max": 10 },
    { "tamano": "L", "puntos_max": 16 },
    { "tamano": "XL", "puntos_max": null }
  ]'::jsonb,
  now(),
  'seed'
)
on conflict (cliente_id, version) do nothing;
