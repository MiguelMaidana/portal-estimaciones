create table if not exists cliente (
  id uuid primary key default gen_random_uuid(),
  nombre text not null,
  servicio text not null,
  linea_base_puntos numeric(10,1) not null,
  activo boolean not null default true
);

create table if not exists usuario (
  id uuid primary key,
  nombre text not null,
  rol text not null,
  cliente_id uuid references cliente(id),
  activo boolean not null default true
);

create table if not exists matriz_sizing (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references cliente(id),
  version integer not null,
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
  estado text not null,
  resultado_completitud text,
  feedback_completitud text,
  sugerencias_mejora jsonb,
  criterios_extraidos jsonb,
  sizing_calculado text,
  puntos_calculados numeric(10,1),
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
  linea_base numeric(10,1) not null,
  consumido numeric(10,1) not null default 0,
  unique (cliente_id, periodo)
);

create table if not exists log_auditoria (
  id uuid primary key default gen_random_uuid(),
  historia_id uuid references historia_usuario(id),
  evento text not null,
  actor text not null,
  detalle jsonb,
  timestamp timestamptz not null default now()
);
