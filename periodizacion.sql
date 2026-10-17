--
-- PostgreSQL database dump
--

\restrict 5Di2guiae22xTPQ9le7avlYtCyS2kLKFIeKYo9fZNsEqjvh59DlsfojkK8e09bF

-- Dumped from database version 18.0
-- Dumped by pg_dump version 18.0

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: periodizacion; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA periodizacion;


ALTER SCHEMA periodizacion OWNER TO postgres;

--
-- Name: SCHEMA periodizacion; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA periodizacion IS 'Esquema para el sistema de periodización de tareas';


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: periodizacion; Owner: postgres
--

CREATE FUNCTION periodizacion.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    NEW.fecha_actualizacion = CURRENT_TIMESTAMP;
    NEW.fecha_ultima_actualizacion = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION periodizacion.update_updated_at_column() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: calendario; Type: TABLE; Schema: periodizacion; Owner: postgres
--

CREATE TABLE periodizacion.calendario (
    id integer NOT NULL,
    tipo_periodizacion character varying(50) NOT NULL,
    descripcion character varying(1200),
    parametros jsonb DEFAULT '{}'::jsonb,
    activo boolean DEFAULT true,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE periodizacion.calendario OWNER TO postgres;

--
-- Name: TABLE calendario; Type: COMMENT; Schema: periodizacion; Owner: postgres
--

COMMENT ON TABLE periodizacion.calendario IS 'Tipos de periodización disponibles para las tareas';


--
-- Name: calendario_id_seq; Type: SEQUENCE; Schema: periodizacion; Owner: postgres
--

CREATE SEQUENCE periodizacion.calendario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE periodizacion.calendario_id_seq OWNER TO postgres;

--
-- Name: calendario_id_seq; Type: SEQUENCE OWNED BY; Schema: periodizacion; Owner: postgres
--

ALTER SEQUENCE periodizacion.calendario_id_seq OWNED BY periodizacion.calendario.id;


--
-- Name: conexion; Type: TABLE; Schema: periodizacion; Owner: postgres
--

CREATE TABLE periodizacion.conexion (
    id_conexion integer NOT NULL,
    tipo character varying(20) NOT NULL,
    nombre character varying(200) NOT NULL,
    usuario character varying(100),
    password text,
    driver character varying(100),
    puerto integer,
    host character varying(200),
    url text,
    cadena_directo text,
    motor character varying(50) NOT NULL,
    activo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT conexion_motor_check CHECK (((motor)::text = ANY (ARRAY[('postgres'::character varying)::text, ('mongo'::character varying)::text, ('mysql'::character varying)::text, ('oracle'::character varying)::text, ('sqlserver'::character varying)::text]))),
    CONSTRAINT conexion_tipo_check CHECK (((tipo)::text = ANY (ARRAY[('wallet'::character varying)::text, ('normal'::character varying)::text])))
);


ALTER TABLE periodizacion.conexion OWNER TO postgres;

--
-- Name: TABLE conexion; Type: COMMENT; Schema: periodizacion; Owner: postgres
--

COMMENT ON TABLE periodizacion.conexion IS 'Conexiones a bases de datos para ejecución de tareas';


--
-- Name: conexion_id_conexion_seq; Type: SEQUENCE; Schema: periodizacion; Owner: postgres
--

CREATE SEQUENCE periodizacion.conexion_id_conexion_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE periodizacion.conexion_id_conexion_seq OWNER TO postgres;

--
-- Name: conexion_id_conexion_seq; Type: SEQUENCE OWNED BY; Schema: periodizacion; Owner: postgres
--

ALTER SEQUENCE periodizacion.conexion_id_conexion_seq OWNED BY periodizacion.conexion.id_conexion;


--
-- Name: descarga; Type: TABLE; Schema: periodizacion; Owner: postgres
--

CREATE TABLE periodizacion.descarga (
    id integer NOT NULL,
    ruta_descarga character varying(500) NOT NULL,
    ruta_respaldo character varying(500),
    estado integer DEFAULT 1 NOT NULL,
    tamanio integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    tipo integer DEFAULT 1 NOT NULL
);


ALTER TABLE periodizacion.descarga OWNER TO postgres;

--
-- Name: descarga_id_seq; Type: SEQUENCE; Schema: periodizacion; Owner: postgres
--

CREATE SEQUENCE periodizacion.descarga_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE periodizacion.descarga_id_seq OWNER TO postgres;

--
-- Name: descarga_id_seq; Type: SEQUENCE OWNED BY; Schema: periodizacion; Owner: postgres
--

ALTER SEQUENCE periodizacion.descarga_id_seq OWNED BY periodizacion.descarga.id;


--
-- Name: detalle_archivos; Type: TABLE; Schema: periodizacion; Owner: postgres
--

CREATE TABLE periodizacion.detalle_archivos (
    id integer NOT NULL,
    archivo character varying(300) NOT NULL,
    numero_filas_consultadas integer DEFAULT 0,
    numero_filas_generadas integer DEFAULT 0,
    numero_filas_copiadas_destino integer DEFAULT 0,
    separador_de_campos character varying(10) DEFAULT '|'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE periodizacion.detalle_archivos OWNER TO postgres;

--
-- Name: detalle_archivos_id_seq; Type: SEQUENCE; Schema: periodizacion; Owner: postgres
--

CREATE SEQUENCE periodizacion.detalle_archivos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE periodizacion.detalle_archivos_id_seq OWNER TO postgres;

--
-- Name: detalle_archivos_id_seq; Type: SEQUENCE OWNED BY; Schema: periodizacion; Owner: postgres
--

ALTER SEQUENCE periodizacion.detalle_archivos_id_seq OWNED BY periodizacion.detalle_archivos.id;


--
-- Name: historico_tarea; Type: TABLE; Schema: periodizacion; Owner: postgres
--

CREATE TABLE periodizacion.historico_tarea (
    id integer NOT NULL,
    nombre character varying(200) NOT NULL,
    fecha_inicio timestamp without time zone NOT NULL,
    fecha_fin timestamp without time zone,
    estado character varying(50) NOT NULL,
    usuario character varying(100) NOT NULL,
    fecha_ejecucion timestamp without time zone NOT NULL,
    duracion numeric(10,2),
    id_tarea integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE periodizacion.historico_tarea OWNER TO postgres;

--
-- Name: TABLE historico_tarea; Type: COMMENT; Schema: periodizacion; Owner: postgres
--

COMMENT ON TABLE periodizacion.historico_tarea IS 'Histórico de ejecuciones de las tareas';


--
-- Name: historico_tarea_id_seq; Type: SEQUENCE; Schema: periodizacion; Owner: postgres
--

CREATE SEQUENCE periodizacion.historico_tarea_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE periodizacion.historico_tarea_id_seq OWNER TO postgres;

--
-- Name: historico_tarea_id_seq; Type: SEQUENCE OWNED BY; Schema: periodizacion; Owner: postgres
--

ALTER SEQUENCE periodizacion.historico_tarea_id_seq OWNED BY periodizacion.historico_tarea.id;


--
-- Name: log_tarea; Type: TABLE; Schema: periodizacion; Owner: postgres
--

CREATE TABLE periodizacion.log_tarea (
    id integer NOT NULL,
    nombre character varying(200) NOT NULL,
    fecha_ejecucion timestamp without time zone NOT NULL,
    novedad text NOT NULL,
    id_tarea integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE periodizacion.log_tarea OWNER TO postgres;

--
-- Name: TABLE log_tarea; Type: COMMENT; Schema: periodizacion; Owner: postgres
--

COMMENT ON TABLE periodizacion.log_tarea IS 'Logs de errores y novedades de las tareas';


--
-- Name: log_tarea_id_seq; Type: SEQUENCE; Schema: periodizacion; Owner: postgres
--

CREATE SEQUENCE periodizacion.log_tarea_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE periodizacion.log_tarea_id_seq OWNER TO postgres;

--
-- Name: log_tarea_id_seq; Type: SEQUENCE OWNED BY; Schema: periodizacion; Owner: postgres
--

ALTER SEQUENCE periodizacion.log_tarea_id_seq OWNED BY periodizacion.log_tarea.id;


--
-- Name: tarea; Type: TABLE; Schema: periodizacion; Owner: postgres
--

CREATE TABLE periodizacion.tarea (
    id integer NOT NULL,
    titulo character varying(200) NOT NULL,
    descripcion text,
    sql text NOT NULL,
    id_calendario integer,
    id_conexion integer,
    fecha_inicio timestamp without time zone NOT NULL,
    fecha_fin timestamp without time zone,
    estado_proceso integer DEFAULT 2 NOT NULL,
    usuario character varying(100) NOT NULL,
    configuracion jsonb DEFAULT '{}'::jsonb,
    task_id_celery character varying(255),
    task_id_dramatiq character varying(255),
    estado_tarea character varying(50) DEFAULT 'pendiente'::character varying,
    resultado text,
    backend_used character varying(50),
    ultimo_mensaje text,
    progreso integer DEFAULT 0,
    celery_interval integer,
    celery_crontab character varying(100),
    celery_args jsonb,
    celery_kwargs jsonb,
    queue character varying(100) DEFAULT 'default'::character varying,
    priority integer DEFAULT 5,
    expires timestamp without time zone,
    last_run_at timestamp without time zone,
    total_run_count integer DEFAULT 0,
    max_retries integer DEFAULT 3,
    retry_delay integer DEFAULT 60,
    one_off boolean DEFAULT false,
    start_time timestamp without time zone,
    enabled boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    fecha_ultima_actualizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    id_descarga integer DEFAULT 1,
    CONSTRAINT tarea_estado_proceso_check CHECK (((estado_proceso >= 1) AND (estado_proceso <= 10)))
);


ALTER TABLE periodizacion.tarea OWNER TO postgres;

--
-- Name: TABLE tarea; Type: COMMENT; Schema: periodizacion; Owner: postgres
--

COMMENT ON TABLE periodizacion.tarea IS 'Tareas programadas para ejecución automática con soporte para Celery';


--
-- Name: COLUMN tarea.sql; Type: COMMENT; Schema: periodizacion; Owner: postgres
--

COMMENT ON COLUMN periodizacion.tarea.sql IS 'Consulta SQL que se ejecutará en la tarea';


--
-- Name: COLUMN tarea.estado_proceso; Type: COMMENT; Schema: periodizacion; Owner: postgres
--

COMMENT ON COLUMN periodizacion.tarea.estado_proceso IS '1:activo, 2:inactivo, 3:detenido, 4:sin respuesta, 5:en ejecucion, 6:bajo demanda, 7:en mantenimiento, 8:en fallo, 9:revise sql, 10:terminado';


--
-- Name: COLUMN tarea.estado_tarea; Type: COMMENT; Schema: periodizacion; Owner: postgres
--

COMMENT ON COLUMN periodizacion.tarea.estado_tarea IS 'Estado de ejecución: pendiente, en_ejecucion, completada, error, cancelada';


--
-- Name: COLUMN tarea.backend_used; Type: COMMENT; Schema: periodizacion; Owner: postgres
--

COMMENT ON COLUMN periodizacion.tarea.backend_used IS 'Backend utilizado para ejecución: celery, dramatiq, etc';


--
-- Name: COLUMN tarea.celery_interval; Type: COMMENT; Schema: periodizacion; Owner: postgres
--

COMMENT ON COLUMN periodizacion.tarea.celery_interval IS 'Intervalo en segundos para ejecución periódica';


--
-- Name: COLUMN tarea.celery_crontab; Type: COMMENT; Schema: periodizacion; Owner: postgres
--

COMMENT ON COLUMN periodizacion.tarea.celery_crontab IS 'Expresión cron para programación avanzada';


--
-- Name: COLUMN tarea.queue; Type: COMMENT; Schema: periodizacion; Owner: postgres
--

COMMENT ON COLUMN periodizacion.tarea.queue IS 'Cola de Celery para la tarea';


--
-- Name: COLUMN tarea.enabled; Type: COMMENT; Schema: periodizacion; Owner: postgres
--

COMMENT ON COLUMN periodizacion.tarea.enabled IS 'Indica si la tarea está habilitada para ejecución';


--
-- Name: tarea_id_seq; Type: SEQUENCE; Schema: periodizacion; Owner: postgres
--

CREATE SEQUENCE periodizacion.tarea_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE periodizacion.tarea_id_seq OWNER TO postgres;

--
-- Name: tarea_id_seq; Type: SEQUENCE OWNED BY; Schema: periodizacion; Owner: postgres
--

ALTER SEQUENCE periodizacion.tarea_id_seq OWNED BY periodizacion.tarea.id;


--
-- Name: calendario id; Type: DEFAULT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.calendario ALTER COLUMN id SET DEFAULT nextval('periodizacion.calendario_id_seq'::regclass);


--
-- Name: conexion id_conexion; Type: DEFAULT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.conexion ALTER COLUMN id_conexion SET DEFAULT nextval('periodizacion.conexion_id_conexion_seq'::regclass);


--
-- Name: descarga id; Type: DEFAULT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.descarga ALTER COLUMN id SET DEFAULT nextval('periodizacion.descarga_id_seq'::regclass);


--
-- Name: detalle_archivos id; Type: DEFAULT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.detalle_archivos ALTER COLUMN id SET DEFAULT nextval('periodizacion.detalle_archivos_id_seq'::regclass);


--
-- Name: historico_tarea id; Type: DEFAULT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.historico_tarea ALTER COLUMN id SET DEFAULT nextval('periodizacion.historico_tarea_id_seq'::regclass);


--
-- Name: log_tarea id; Type: DEFAULT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.log_tarea ALTER COLUMN id SET DEFAULT nextval('periodizacion.log_tarea_id_seq'::regclass);


--
-- Name: tarea id; Type: DEFAULT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.tarea ALTER COLUMN id SET DEFAULT nextval('periodizacion.tarea_id_seq'::regclass);


--
-- Data for Name: calendario; Type: TABLE DATA; Schema: periodizacion; Owner: postgres
--

COPY periodizacion.calendario (id, tipo_periodizacion, descripcion, parametros, activo, fecha_creacion) FROM stdin;
1	diario	Ejecución diaria	{"hora": "06:00"}	t	2025-10-02 13:20:08.728156
2	semanal	Ejecución semanal los lunes	{"dia": "lunes", "hora": "06:00"}	t	2025-10-02 13:20:08.728156
3	mensual	Ejecución mensual el día 1	{"dia": 1, "hora": "06:00"}	t	2025-10-02 13:20:08.728156
4	quincenal	Ejecución los días 1 y 15	{"dias": [1, 15], "hora": "06:00"}	t	2025-10-02 13:20:08.728156
5	cada_n_horas	Cada cierto numero de horas	{"horas": 6}	t	2025-10-02 13:20:08.728156
6	cada_n_minutos	Cada cierto numero de minutos	{"minutos": 15}	t	2025-10-02 13:20:08.728156
7	dia_determinado	Ejecución dia especifico	{"dia": "lunes", "hora": "06:00"}	t	2025-10-02 13:20:08.728156
8	ocasional	Ejecución ocasional	{"dias": [1, 15], "hora": "06:00"}	t	2025-10-02 13:20:08.728156
9	unica	Ejecución única	{"dias": [8], "hora": "06:00"}	t	2025-10-02 13:20:08.728156
\.


--
-- Data for Name: conexion; Type: TABLE DATA; Schema: periodizacion; Owner: postgres
--

COPY periodizacion.conexion (id_conexion, tipo, nombre, usuario, password, driver, puerto, host, url, cadena_directo, motor, activo, created_at, updated_at) FROM stdin;
1	normal	PostgreSQL Local	postgres	jdfoxito10	psycopg	5432	192.168.100.4	\N	postgresql://postgres:jdfoxito10@localhost:5432/seguimientodb	postgres	t	2025-10-02 13:20:08.74391	2025-10-02 13:20:08.74391
2	wallet	BI_DWH	\N	\N	\N	\N	\N	D:\\oracle\\WINDOWS.X64_193000_db_home\\bin	\N	oracle	t	2025-10-02 13:20:08.74391	2025-10-02 13:20:08.74391
4	normal	CADENAS	postgres	jdfoxito10	devoluciones	5432	10.21.178.245	\N	\N	postgres	t	2025-10-02 21:20:16.190436	2025-10-02 21:20:16.190671
5	normal	SEGUIMIENTO	postgres	jdfoxito10	seguimientodb	5432	10.21.178.245	\N	\N	postgres	t	2025-10-03 14:55:12.191688	2025-10-03 14:55:12.192121
6	wallet	DETALLES	\N	\N	\N	\N	\N	D:\\softapps\\ora21cli\\oraclient	D:\\oracle\\wallet\\ai23	oracle	t	2025-10-21 16:23:40.078258	2025-10-21 16:23:40.078674
\.


--
-- Data for Name: descarga; Type: TABLE DATA; Schema: periodizacion; Owner: postgres
--

COPY periodizacion.descarga (id, ruta_descarga, ruta_respaldo, estado, tamanio, created_at, tipo) FROM stdin;
1	/root/tracker/trackerApp/archivos		1	1	2025-10-14 19:00:56.278271	1
\.


--
-- Data for Name: detalle_archivos; Type: TABLE DATA; Schema: periodizacion; Owner: postgres
--

COPY periodizacion.detalle_archivos (id, archivo, numero_filas_consultadas, numero_filas_generadas, numero_filas_copiadas_destino, separador_de_campos, created_at) FROM stdin;
\.


--
-- Data for Name: historico_tarea; Type: TABLE DATA; Schema: periodizacion; Owner: postgres
--

COPY periodizacion.historico_tarea (id, nombre, fecha_inicio, fecha_fin, estado, usuario, fecha_ejecucion, duracion, id_tarea, created_at) FROM stdin;
\.


--
-- Data for Name: log_tarea; Type: TABLE DATA; Schema: periodizacion; Owner: postgres
--

COPY periodizacion.log_tarea (id, nombre, fecha_ejecucion, novedad, id_tarea, created_at) FROM stdin;
\.


--
-- Data for Name: tarea; Type: TABLE DATA; Schema: periodizacion; Owner: postgres
--

COPY periodizacion.tarea (id, titulo, descripcion, sql, id_calendario, id_conexion, fecha_inicio, fecha_fin, estado_proceso, usuario, configuracion, task_id_celery, task_id_dramatiq, estado_tarea, resultado, backend_used, ultimo_mensaje, progreso, celery_interval, celery_crontab, celery_args, celery_kwargs, queue, priority, expires, last_run_at, total_run_count, max_retries, retry_delay, one_off, start_time, enabled, created_at, updated_at, fecha_creacion, fecha_actualizacion, fecha_ultima_actualizacion, id_descarga) FROM stdin;
4	titulo	titlo 2023	select * from public.cambio where estado_de_la_fase not in ('Cerrado');	1	5	2025-09-27 13:00:00	\N	10	jagonzalezj@sri.gob.ec	{}	8534b1fc-4163-463c-af80-b57bf82fd3c7	\N	completada	/datos/tarea_4_20251024_102338.csv	celery	Tarea completada - Método: tradicional - Archivo: tarea_4_20251024_102338.csv	100	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-02 13:20:08.763567	2025-10-24 10:27:28.122283	2025-10-02 13:20:08.763567	2025-10-24 10:27:28.122283	2025-10-24 10:27:28.122283	1
5	intento	ntento	select * from public.reloj_detalle where descripcion ilike '%analista%';	1	5	2025-09-25 13:00:00	\N	10	jagonzalezj@sri.gob.ec	{}	748a1558-c8e7-4c54-aaf0-cf83f26b6672	\N	completada	/datos/tarea_5_20251024_102339.csv	celery	Tarea completada - Método: tradicional - Archivo: tarea_5_20251024_102339.csv	100	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-02 13:20:08.763567	2025-10-24 10:27:30.03603	2025-10-02 13:20:08.763567	2025-10-24 10:27:30.03603	2025-10-24 10:27:30.03603	1
2	Backup semanal de incidentes	Respaldo semanal de la tabla incidentes	SELECT * FROM public.requerimiento WHERE fecha_apertura >= CURRENT_DATE - INTERVAL '71 days';	2	5	2025-09-25 00:50:57.189913	\N	10	admin	{}	cd4ab1d9-2536-42b4-87ed-f1f5cf6dc850	\N	completada	/datos/tarea_2_20251024_102335.csv	celery	Tarea completada - Método: tradicional - Archivo: tarea_2_20251024_102335.csv	100	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-02 13:20:08.763567	2025-10-24 10:27:25.744986	2025-10-02 13:20:08.763567	2025-10-24 10:27:25.744986	2025-10-24 10:27:25.744986	1
21	 ELEC SPARK	retenciones electronicas via spark	select *from BI_DWH.DEV_IVA_RETENCION_ON_ELEC	1	2	2025-10-14 13:00:00	\N	10	jagonzaj@sri.gob.ec	{}	df76dd4e-c4ab-4dbc-bc78-335a5e62204d	\N	completada	/datos/tarea_21_20251028_103448.csv	celery	Tarea completada - Método: tradicional - Archivo: tarea_21_20251028_103448.csv	100	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-14 10:36:40.712734	2025-10-28 10:36:56.681967	2025-10-14 15:36:40.718005	2025-10-28 10:36:56.681967	2025-10-28 10:36:56.681967	1
17	rentenciones fiscas 93600		select *from terceros.dev_iva_retencion_on_fi limit 93600;	1	4	2025-10-02 13:00:00	\N	5	jagonzaj@sri.gob.ec	{}	be31873b-a5bb-45e1-b5ed-aabdc801518a	\N	completada	/datos/tarea_17_20251024_102647.csv	celery	Tarea completada - Método: tradicional - Archivo: tarea_17_20251024_102647.csv	100	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-02 11:57:43.78991	2025-11-14 11:57:47.243512	2025-10-02 16:57:43.793032	2025-11-14 11:57:47.243512	2025-11-14 11:57:47.243512	1
18	CARGA RETENCIONES FISICAS	RETENCIONES FISICAS SOLO FISICAS	select *from terceros.dev_iva_retencion_on_fi limit 10000;	1	4	2025-10-02 21:18:00	\N	5	jagonzaj@sri.gob.ec	{}	b3c166fc-20f0-4b33-96ae-abec92e14454	\N	completada	/datos/tarea_18_20251024_102730.csv	celery	Tarea completada - Método: tradicional - Archivo: tarea_18_20251024_102730.csv	100	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-02 16:21:56.932021	2025-11-14 11:57:48.5843	2025-10-02 21:21:56.93499	2025-11-14 11:57:48.5843	2025-11-14 11:57:48.5843	1
19	bi_swh	conexion a la  bi dwh	select * from  BI_DWH.BDW_TRAZABILIDAD_CABECERA_INFO	1	2	2025-10-03 13:00:00	\N	5	jagonzaj@sri.gob.ec	{}	2bb78182-b89f-4964-b2b8-c8a8584ca6d9	\N	completada	/datos/tarea_19_20251024_110647.csv	celery	Tarea completada - Método: tradicional - Archivo: tarea_19_20251024_110647.csv	100	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-03 10:01:41.694727	2025-11-14 11:57:58.85327	2025-10-03 15:01:41.699474	2025-11-14 11:57:58.85327	2025-11-14 11:57:58.85327	1
23	DETALLES 10mill on cel_factura_detalle	probando a la de detalles	select * from cel_factura_detalle	1	6	2025-10-21 13:00:00	\N	2	jagonzaj@sri.gob.ec	{}	73022892-8c36-4e3c-98dd-2358aa2baa4b	\N	error	\N	celery	Error: SoftTimeLimitExceeded()	0	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-21 11:30:19.433413	2025-11-14 16:57:34.638713	2025-10-21 16:30:19.450523	2025-11-14 16:57:34.638713	2025-11-14 16:57:34.638713	1
25	partial	seria solo 1millon	select * from cel_factura_detalle where rownum < 1000000	1	6	2025-10-22 19:20:00	\N	2	jagonzaj@sri.gob.ec	{}	63784d8c-4177-436d-9743-77b6b57695d7	\N	completada	/datos/tarea_25_20251028_151409.csv	celery	Tarea completada - Método: tradicional - Archivo: tarea_25_20251028_151409.csv	100	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-22 14:34:40.516534	2025-11-14 16:57:34.638713	2025-10-22 19:34:40.598465	2025-11-14 16:57:34.638713	2025-11-14 16:57:34.638713	1
14	retencioes fisicas 100k	fiscas de cadenas de iva	select *from terceros.dev_iva_retencion_on_fi limit 100000;	2	4	2025-10-02 13:00:00	\N	2	jagonzaj@sri.gob.ec	{}	b0777c7f-d557-4497-acc6-c19515b10930	\N	completada	/datos/tarea_14_20251024_102730.csv	celery	Tarea completada - Método: tradicional - Archivo: tarea_14_20251024_102730.csv	100	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-02 11:38:45.051392	2025-11-14 16:57:34.638713	2025-10-02 16:38:45.054938	2025-11-14 16:57:34.638713	2025-11-14 16:57:34.638713	1
22	solo unas mil electricas	elctricas 10000	select *from BI_DWH.DEV_IVA_RETENCION_ON_ELEC where rownum < 1000	1	2	2025-10-14 19:47:00	\N	2	jagonzaj@sri.gob.ec	{}	aa61ff09-0f04-4528-8b0c-32c04c16f7f8	\N	completada	/datos/tarea_22_20251024_110223.csv	celery	Tarea completada - Método: tradicional - Archivo: tarea_22_20251024_110223.csv	100	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-14 14:57:28.057481	2025-11-14 16:57:34.638713	2025-10-14 19:57:28.063364	2025-11-14 16:57:34.638713	2025-11-14 16:57:34.638713	1
1	Estadísticas mensuales	Estadísticas mensuales de requerimientos	SELECT estado_actual, COUNT(*) FROM public.requerimiento WHERE EXTRACT(MONTH FROM fecha_apertura) = EXTRACT(MONTH FROM CURRENT_DATE) GROUP BY estado_actual;	3	5	2025-09-25 00:50:57.189913	\N	2	sistema	{}	93ee3b39-6455-4691-b72c-34d177b033c1	\N	completada	/datos/tarea_1_20251024_102335.csv	celery	Tarea completada - Método: tradicional - Archivo: tarea_1_20251024_102335.csv	100	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-02 13:20:08.763567	2025-11-14 16:57:34.638713	2025-10-02 13:20:08.763567	2025-11-14 16:57:34.638713	2025-11-14 16:57:34.638713	1
3	Reporte diario de cambios	Genera reporte diario de cambios realizados	SELECT * FROM public.incidente WHERE fecha_apertura >= CURRENT_DATE - INTERVAL '321 day';	1	5	2025-09-25 00:50:57.189913	\N	2	admin	{}	f20a9ebb-8c94-4370-b5bb-169c8b07450c	\N	completada	/datos/tarea_3_20251024_102332.csv	celery	Tarea completada - Método: tradicional - Archivo: tarea_3_20251024_102332.csv	100	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-02 13:20:08.763567	2025-11-14 16:57:34.638713	2025-10-02 13:20:08.763567	2025-11-14 16:57:34.638713	2025-11-14 16:57:34.638713	1
16	retencioes fisicas 1m	alskd	select *from terceros.dev_iva_retencion_on_fi limit 1000000;	1	4	2025-10-02 13:00:00	\N	5	jagonzaj@sri.gob.ec	{}	78fcd1e5-80ab-4941-9b86-8197a5c3c86f	\N	completada	/datos/tarea_16_20251024_102720.csv	celery	Tarea completada - Método: tradicional - Archivo: tarea_16_20251024_102720.csv	100	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-02 11:57:02.46196	2025-11-14 11:57:44.05672	2025-10-02 16:57:02.465894	2025-11-14 11:57:44.05672	2025-11-14 11:57:44.05672	1
20	fisicas 23ai	pueba a retenciones fisicas,	select *from  BI_DWH.DEV_IVA_RETENCION_ON_FI	1	2	2025-10-08 13:00:00	\N	5	jagonzaj@sri.gob.ec	{}	869c6501-441d-4163-ab3a-0c43290603c4	\N	completada	/datos/tarea_20_20251024_110631.csv	celery	Tarea completada - Método: tradicional - Archivo: tarea_20_20251024_110631.csv	100	\N	\N	\N	\N	default	5	\N	\N	0	3	60	f	\N	t	2025-10-08 12:30:52.461182	2025-11-14 11:57:50.385801	2025-10-08 17:30:52.477315	2025-11-14 11:57:50.385801	2025-11-14 11:57:50.385801	1
\.


--
-- Name: calendario_id_seq; Type: SEQUENCE SET; Schema: periodizacion; Owner: postgres
--

SELECT pg_catalog.setval('periodizacion.calendario_id_seq', 9, true);


--
-- Name: conexion_id_conexion_seq; Type: SEQUENCE SET; Schema: periodizacion; Owner: postgres
--

SELECT pg_catalog.setval('periodizacion.conexion_id_conexion_seq', 6, true);


--
-- Name: descarga_id_seq; Type: SEQUENCE SET; Schema: periodizacion; Owner: postgres
--

SELECT pg_catalog.setval('periodizacion.descarga_id_seq', 1, false);


--
-- Name: detalle_archivos_id_seq; Type: SEQUENCE SET; Schema: periodizacion; Owner: postgres
--

SELECT pg_catalog.setval('periodizacion.detalle_archivos_id_seq', 1, false);


--
-- Name: historico_tarea_id_seq; Type: SEQUENCE SET; Schema: periodizacion; Owner: postgres
--

SELECT pg_catalog.setval('periodizacion.historico_tarea_id_seq', 1, false);


--
-- Name: log_tarea_id_seq; Type: SEQUENCE SET; Schema: periodizacion; Owner: postgres
--

SELECT pg_catalog.setval('periodizacion.log_tarea_id_seq', 1, false);


--
-- Name: tarea_id_seq; Type: SEQUENCE SET; Schema: periodizacion; Owner: postgres
--

SELECT pg_catalog.setval('periodizacion.tarea_id_seq', 25, true);


--
-- Name: calendario calendario_pkey; Type: CONSTRAINT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.calendario
    ADD CONSTRAINT calendario_pkey PRIMARY KEY (id);


--
-- Name: conexion conexion_nombre_key; Type: CONSTRAINT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.conexion
    ADD CONSTRAINT conexion_nombre_key UNIQUE (nombre);


--
-- Name: conexion conexion_pkey; Type: CONSTRAINT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.conexion
    ADD CONSTRAINT conexion_pkey PRIMARY KEY (id_conexion);


--
-- Name: descarga descarga_pkey; Type: CONSTRAINT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.descarga
    ADD CONSTRAINT descarga_pkey PRIMARY KEY (id);


--
-- Name: detalle_archivos detalle_archivos_pkey; Type: CONSTRAINT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.detalle_archivos
    ADD CONSTRAINT detalle_archivos_pkey PRIMARY KEY (id);


--
-- Name: historico_tarea historico_tarea_pkey; Type: CONSTRAINT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.historico_tarea
    ADD CONSTRAINT historico_tarea_pkey PRIMARY KEY (id);


--
-- Name: log_tarea log_tarea_pkey; Type: CONSTRAINT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.log_tarea
    ADD CONSTRAINT log_tarea_pkey PRIMARY KEY (id);


--
-- Name: tarea tarea_pkey; Type: CONSTRAINT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.tarea
    ADD CONSTRAINT tarea_pkey PRIMARY KEY (id);


--
-- Name: idx_calendario_tipo; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_calendario_tipo ON periodizacion.calendario USING btree (tipo_periodizacion);


--
-- Name: idx_conexion_activo; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_conexion_activo ON periodizacion.conexion USING btree (activo);


--
-- Name: idx_conexion_motor; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_conexion_motor ON periodizacion.conexion USING btree (motor);


--
-- Name: idx_conexion_nombre; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_conexion_nombre ON periodizacion.conexion USING btree (nombre);


--
-- Name: idx_historico_tarea_fecha; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_historico_tarea_fecha ON periodizacion.historico_tarea USING btree (fecha_ejecucion);


--
-- Name: idx_historico_tarea_id; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_historico_tarea_id ON periodizacion.historico_tarea USING btree (id_tarea);


--
-- Name: idx_log_tarea_fecha; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_log_tarea_fecha ON periodizacion.log_tarea USING btree (fecha_ejecucion);


--
-- Name: idx_log_tarea_id; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_log_tarea_id ON periodizacion.log_tarea USING btree (id_tarea);


--
-- Name: idx_tarea_backend_used; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_tarea_backend_used ON periodizacion.tarea USING btree (backend_used);


--
-- Name: idx_tarea_enabled; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_tarea_enabled ON periodizacion.tarea USING btree (enabled);


--
-- Name: idx_tarea_estado; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_tarea_estado ON periodizacion.tarea USING btree (estado_proceso);


--
-- Name: idx_tarea_estado_tarea; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_tarea_estado_tarea ON periodizacion.tarea USING btree (estado_tarea);


--
-- Name: idx_tarea_fecha_inicio; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_tarea_fecha_inicio ON periodizacion.tarea USING btree (fecha_inicio);


--
-- Name: idx_tarea_id_calendario; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_tarea_id_calendario ON periodizacion.tarea USING btree (id_calendario);


--
-- Name: idx_tarea_id_conexion; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_tarea_id_conexion ON periodizacion.tarea USING btree (id_conexion);


--
-- Name: idx_tarea_last_run_at; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_tarea_last_run_at ON periodizacion.tarea USING btree (last_run_at);


--
-- Name: idx_tarea_queue; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_tarea_queue ON periodizacion.tarea USING btree (queue);


--
-- Name: idx_tarea_task_id_celery; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_tarea_task_id_celery ON periodizacion.tarea USING btree (task_id_celery);


--
-- Name: idx_tarea_usuario; Type: INDEX; Schema: periodizacion; Owner: postgres
--

CREATE INDEX idx_tarea_usuario ON periodizacion.tarea USING btree (usuario);


--
-- Name: conexion update_conexion_updated_at; Type: TRIGGER; Schema: periodizacion; Owner: postgres
--

CREATE TRIGGER update_conexion_updated_at BEFORE UPDATE ON periodizacion.conexion FOR EACH ROW EXECUTE FUNCTION periodizacion.update_updated_at_column();


--
-- Name: tarea update_tarea_updated_at; Type: TRIGGER; Schema: periodizacion; Owner: postgres
--

CREATE TRIGGER update_tarea_updated_at BEFORE UPDATE ON periodizacion.tarea FOR EACH ROW EXECUTE FUNCTION periodizacion.update_updated_at_column();


--
-- Name: historico_tarea historico_tarea_id_tarea_fkey; Type: FK CONSTRAINT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.historico_tarea
    ADD CONSTRAINT historico_tarea_id_tarea_fkey FOREIGN KEY (id_tarea) REFERENCES periodizacion.tarea(id) ON DELETE CASCADE;


--
-- Name: log_tarea log_tarea_id_tarea_fkey; Type: FK CONSTRAINT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.log_tarea
    ADD CONSTRAINT log_tarea_id_tarea_fkey FOREIGN KEY (id_tarea) REFERENCES periodizacion.tarea(id) ON DELETE CASCADE;


--
-- Name: tarea tarea_id_calendario_fkey; Type: FK CONSTRAINT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.tarea
    ADD CONSTRAINT tarea_id_calendario_fkey FOREIGN KEY (id_calendario) REFERENCES periodizacion.calendario(id) ON DELETE SET NULL;


--
-- Name: tarea tarea_id_conexion_fkey; Type: FK CONSTRAINT; Schema: periodizacion; Owner: postgres
--

ALTER TABLE ONLY periodizacion.tarea
    ADD CONSTRAINT tarea_id_conexion_fkey FOREIGN KEY (id_conexion) REFERENCES periodizacion.conexion(id_conexion) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict 5Di2guiae22xTPQ9le7avlYtCyS2kLKFIeKYo9fZNsEqjvh59DlsfojkK8e09bF

