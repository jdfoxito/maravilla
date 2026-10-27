# -*- coding: utf-8 -*-
"""
analisis_gad_cero_mb.py
=======================
Seguimiento al memo DNRAC: anexos GAD que aparecen con peso "0 MB".

Pregunta de negocio
    ¿Los anexos GAD registrados con 0 MB tienen realmente cero registros,
    o el sistema (RIG) sí grabó cabecera / detalle?

Qué hace
    1. Extrae de RIG (vía dblink @db_sri, conexión por wallet a STAR):
         - RIG_REGISTRO_ANEXO        (estado, tamaño crudo, TOTAL_REGISTROS, período)
         - conteos por anexo de cabecera, bienes inmuebles, espectáculos,
           artistas y localidades (todos los estados y solo CDEF)
         - señales de RUC de prueba (datos genéricos en el detalle)
         - opcional: ODS_GAD_CONSOLIDADO_INMUEBLE para reconciliar
    2. Cruza todo por CODIGO_REGISTRO_ANEXO y clasifica cada anexo.
    3. Detecta anomalías (ver CATALOGO_ANOMALIAS).
    4. Genera:
         - salida/analisis_gad_cero_mb_<fecha>.xlsx   (listados para revisar)
         - salida/reporte_gad_cero_mb_<fecha>.html    (gráficas + justificación)

Uso
    python analisis_gad_cero_mb.py                         # BD -> análisis
    python analisis_gad_cero_mb.py --guardar-csv           # además guarda extractos
    python analisis_gad_cero_mb.py --desde-csv salida/extractos   # sin BD

Requisitos (todos open source)
    pip install oracledb pandas openpyxl matplotlib

Nota wallet: la autenticación por "secure external password store"
(mkstore -createCredential) sigue requiriendo thick mode en python-oracledb;
el thin mode solo soporta wallets de TLS (ewallet.pem), no externalauth.
"""

from __future__ import annotations

import argparse
import base64
import html
import io
import logging
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# ==========================================================================
# CONFIGURACIÓN
# ==========================================================================
DSN_RIG = os.environ.get("DSN_RIG", "STAR")          # BD desde donde se ve rig.*@db_sri
DSN_ODS = os.environ.get("DSN_ODS", "")              # "" = no reconciliar con el ODS
TABLA_ODS = os.environ.get("TABLA_ODS", "ODS_GAD_CONSOLIDADO_INMUEBLE")

ANIO_DESDE = 2022                                     # fecha de presentación (incluido)
ANIO_HASTA = 2026                                     # fecha de presentación (incluido)

WALLET_WINDOWS = r"D:\oracle\WallFiscalProd"
ORACLE_HOME_WINDOWS = r"D:\softapps\ora21cli\product\21.0.0\client_1"

DIR_SALIDA = Path(os.environ.get("DIR_SALIDA", "./salida"))

# RUC confirmados como prueba (se excluyen siempre)
RUCS_PRUEBA = {"1768140710001"}
# True: también se excluyen los RUC con datos genéricos (CONTRIBUYENTE ABC, ESTE CAMPO...).
# Igual se listan en la hoja "Posibles_prueba" para validarlos.
EXCLUIR_SOSPECHOSOS_PRUEBA = True

# Cuántas filas en la hoja "Top" (los principales casos a revisar)
TOP_N = 1000

# La DNRAC calcula "MB" como round(TAMANIO_ARCHIVO_ANEXO / 1024, 2)
DIVISOR_DNRAC = 1024
DECIMALES_DNRAC = 2
UNIDAD_CRUDA = "KB"   # unidad supuesta de TAMANIO_ARCHIVO_ANEXO (confirmar)

TOPES_EXCEL = [(65530, 65540, "xls 65.536"), (1048570, 1048580, "xlsx 1.048.576")]
CAIDA_MIN_PREVIO = 10      # predios mínimos el año anterior para evaluar caída
CAIDA_UMBRAL = 0.5         # caída >= 50 %

ESTADOS = {
    "CDEF": "Carga definitiva",
    "SUS": "Sustituida",
    "FAL": "Fallida",
    "RIDE": "RIDE",
    "CAR": "Cargado",
    "VAL": "Validado",
}

CATALOGO_ANOMALIAS = {
    "A01_CERO_CON_DETALLE":   "CDEF con 0 MB pero con detalle grabado (el 0 es redondeo)",
    "A02_CERO_VACIO":         "CDEF con 0 MB y sin detalle grabado (vacío real)",
    "A03_CDEF_SIN_DETALLE":   "CDEF con peso > 0 pero sin detalle grabado",
    "A04_DETALLE_NO_CDEF":    "CDEF cuyo detalle no está en CDEF (no llega al ODS)",
    "A05_TOTAL_NO_CUADRA":    "TOTAL_REGISTROS no coincide con lo grabado en detalle",
    "A06_TOPE_EXCEL":         "Conteo pegado al tope de Excel (posible archivo truncado)",
    "A07_CAIDA_BRUSCA":       "Caída >= 50 % de predios frente al período anterior del GAD",
    "A08_TAMANIO_CRUDO_0":    "Tamaño crudo exactamente 0 o nulo",
    "A09_FALLIDO_CON_DETALLE": "Fallido/Suspendido que dejó filas de detalle grabadas",
    "A10_CDEF_MULTIPLE":      "Más de un CDEF vigente para el mismo RUC y período",
    "A11_ODS_NO_CUADRA":      "Predios originales en ODS distintos a los CDEF de RIG",
    "A12_ODS_DUPLICADO":      "Copias del arrastre insertadas en el mismo año (bug paquete)",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("gad_cero_mb")


# ==========================================================================
# SQL
# ==========================================================================
_FILTRO_REG = """
    r.codigo_operativo = 'GAD'
    and r.fecha_presentacion >= :desde
    and r.fecha_presentacion <  :hasta"""

SQL_REGISTROS = f"""
select r.codigo_registro_anexo,
       r.identificacion_informante,
       r.codigo_anio               periodo_fiscal,
       r.estado_carga,
       r.fecha_presentacion,
       r.fecha_fin_proceso,
       r.tamanio_archivo_anexo     tamanio_crudo,
       r.total_registros
from   rig.rig_registro_anexo@db_sri r
where  {_FILTRO_REG}"""

SQL_DETALLE = {
    "cab": f"""
select /*+ driving_site(c) */ c.codigo_registro_anexo, count(*) n_cab
from   rig.rig_gad_cabecera@db_sri c
join   rig.rig_registro_anexo@db_sri r on r.codigo_registro_anexo = c.codigo_registro_anexo
where  {_FILTRO_REG}
group  by c.codigo_registro_anexo""",
    "bien": f"""
select /*+ driving_site(b) */ c.codigo_registro_anexo,
       count(*) n_bien,
       sum(case when b.estado_carga = 'CDEF' then 1 else 0 end) n_bien_cdef
from   rig.rig_gad_cabecera@db_sri c
join   rig.rig_gad_bien_inmueble@db_sri b on b.codigo_gad_cabecera = c.codigo_gad_cabecera
join   rig.rig_registro_anexo@db_sri r    on r.codigo_registro_anexo = c.codigo_registro_anexo
where  {_FILTRO_REG}
group  by c.codigo_registro_anexo""",
    "esp": f"""
select /*+ driving_site(e) */ c.codigo_registro_anexo,
       count(*) n_esp,
       sum(case when e.estado_carga = 'CDEF' then 1 else 0 end) n_esp_cdef
from   rig.rig_gad_cabecera@db_sri c
join   rig.rig_gad_espectaculo@db_sri e on e.codigo_gad_cabecera = c.codigo_gad_cabecera
join   rig.rig_registro_anexo@db_sri r  on r.codigo_registro_anexo = c.codigo_registro_anexo
where  {_FILTRO_REG}
group  by c.codigo_registro_anexo""",
    "art": f"""
select /*+ driving_site(a) */ c.codigo_registro_anexo,
       count(*) n_art,
       sum(case when a.estado_carga = 'CDEF' then 1 else 0 end) n_art_cdef
from   rig.rig_gad_cabecera@db_sri c
join   rig.rig_gad_espectaculo@db_sri e on e.codigo_gad_cabecera = c.codigo_gad_cabecera
join   rig.rig_gad_artista@db_sri a     on a.codigo_gad_espectaculo = e.codigo_gad_espectaculo
join   rig.rig_registro_anexo@db_sri r  on r.codigo_registro_anexo = c.codigo_registro_anexo
where  {_FILTRO_REG}
group  by c.codigo_registro_anexo""",
    "loc": f"""
select /*+ driving_site(l) */ c.codigo_registro_anexo,
       count(*) n_loc,
       sum(case when l.estado_carga = 'CDEF' then 1 else 0 end) n_loc_cdef
from   rig.rig_gad_cabecera@db_sri c
join   rig.rig_gad_espectaculo@db_sri e on e.codigo_gad_cabecera = c.codigo_gad_cabecera
join   rig.rig_gad_localidad@db_sri l   on l.codigo_gad_espectaculo = e.codigo_gad_espectaculo
join   rig.rig_registro_anexo@db_sri r  on r.codigo_registro_anexo = c.codigo_registro_anexo
where  {_FILTRO_REG}
group  by c.codigo_registro_anexo""",
}

SQL_PRUEBA = f"""
select /*+ driving_site(b) */ r.identificacion_informante, c.codigo_registro_anexo,
       count(*) n_filas_genericas
from   rig.rig_gad_cabecera@db_sri c
join   rig.rig_gad_bien_inmueble@db_sri b on b.codigo_gad_cabecera = c.codigo_gad_cabecera
join   rig.rig_registro_anexo@db_sri r    on r.codigo_registro_anexo = c.codigo_registro_anexo
where  {_FILTRO_REG}
and   (upper(b.razon_social_bien)     like '%CONTRIBUYENTE ABC%'
    or upper(b.razon_social_bien)     like '%PRUEBA%'
    or upper(b.otro_tipo_bien)        like '%ESTE CAMPO%'
    or upper(b.otro_tipo_transaccion) like '%ESTE CAMPO%'
    or upper(b.id_identificacion)     like 'PASAPORTE1234%')
group  by r.identificacion_informante, c.codigo_registro_anexo"""

SQL_ODS = f"""
select codigo_registro_anexo,
       count(*) n_ods,
       sum(case when instr(seguimiento, ',', 1, 2) = 0 then 1 else 0 end) n_ods_original
from   {TABLA_ODS}
where  fuente_informacion = 'RIG'
group  by codigo_registro_anexo"""


# ==========================================================================
# CONEXIÓN ORACLE CON WALLET (thick + externalauth)
# ==========================================================================
class ConexionOracleWallet:
    """Conexión standalone con wallet (las credenciales las resuelve mkstore)."""

    _cliente_iniciado = False

    def __init__(self, dsn: str, wallet_path: Optional[str] = None):
        import oracledb  # import diferido: --desde-csv no necesita el driver
        self.oracledb = oracledb
        self.dsn = dsn
        self._configurar_cliente(wallet_path)
        self.conn = None

    def _configurar_cliente(self, wallet_path: Optional[str]):
        if platform.system() == "Windows":
            os.environ["TNS_ADMIN"] = wallet_path or os.environ.get("TNS_ADMIN", WALLET_WINDOWS)
            os.environ.setdefault("ORACLE_HOME", ORACLE_HOME_WINDOWS)
        elif not os.environ.get("TNS_ADMIN") and Path("/opt/oracle/wallets").exists():
            os.environ["TNS_ADMIN"] = "/opt/oracle/wallets"
        log.info("TNS_ADMIN = %s", os.environ.get("TNS_ADMIN"))
        if not ConexionOracleWallet._cliente_iniciado:
            try:
                self.oracledb.init_oracle_client()
            except self.oracledb.Error as exc:  # ya iniciado
                log.warning("init_oracle_client: %s", exc)
            ConexionOracleWallet._cliente_iniciado = True

    def __enter__(self):
        self.conn = self.oracledb.connect(dsn=self.dsn, externalauth=True)
        log.info("Conectado a %s", self.dsn)
        return self

    def __exit__(self, *exc):
        if self.conn:
            self.conn.close()

    def consulta_df(self, sql: str, params: Optional[dict] = None) -> pd.DataFrame:
        with self.conn.cursor() as cur:
            cur.arraysize = 20_000
            cur.prefetchrows = 20_001
            cur.execute(sql, params or {})
            cols = [d[0].lower() for d in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)


# ==========================================================================
# EXTRACCIÓN
# ==========================================================================
def extraer_bd() -> dict[str, pd.DataFrame]:
    params = {"desde": datetime(ANIO_DESDE, 1, 1), "hasta": datetime(ANIO_HASTA + 1, 1, 1)}
    datos: dict[str, pd.DataFrame] = {}
    with ConexionOracleWallet(DSN_RIG) as cx:
        datos["registros"] = cx.consulta_df(SQL_REGISTROS, params)
        log.info("registros: %s", len(datos["registros"]))
        for nombre, sql in SQL_DETALLE.items():
            datos[nombre] = cx.consulta_df(sql, params)
            log.info("%s: %s anexos con filas", nombre, len(datos[nombre]))
        datos["prueba"] = cx.consulta_df(SQL_PRUEBA, params)
        log.info("anexos con datos genéricos: %s", len(datos["prueba"]))

    datos["ods"] = pd.DataFrame()
    if DSN_ODS:
        try:
            with ConexionOracleWallet(DSN_ODS) as cx:
                datos["ods"] = cx.consulta_df(SQL_ODS)
            log.info("ods: %s anexos", len(datos["ods"]))
        except Exception as exc:  # noqa: BLE001 - el ODS es opcional
            log.warning("No se pudo leer el ODS (%s); se omite la reconciliación", exc)
    return datos


def guardar_csv(datos: dict[str, pd.DataFrame], carpeta: Path):
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, df in datos.items():
        df.to_csv(carpeta / f"{nombre}.csv", index=False, sep=";")
    log.info("Extractos guardados en %s", carpeta.resolve())


def leer_csv(carpeta: Path) -> dict[str, pd.DataFrame]:
    datos = {}
    for nombre in ["registros", *SQL_DETALLE, "prueba", "ods"]:
        f = carpeta / f"{nombre}.csv"
        datos[nombre] = (pd.read_csv(f, sep=";", dtype={"identificacion_informante": str})
                         if f.exists() and f.stat().st_size > 1 else pd.DataFrame())
    return datos


# ==========================================================================
# ANÁLISIS
# ==========================================================================
def _clasificar_detalle(row) -> str:
    if row.n_cab == 0:
        return "1. Sin cabecera"
    if row.n_bien + row.n_esp == 0:
        return "2. Solo cabecera"
    if row.n_esp == 0:
        return "3. Solo inmuebles"
    if row.n_bien == 0:
        return "4. Solo espectáculos"
    return "5. Inmuebles y espectáculos"


def _detectar_formula(df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    """Busca qué suma de tablas reproduce TOTAL_REGISTROS en los CDEF."""
    candidatas = {
        "bien + esp": ["n_bien", "n_esp"],
        "bien + esp + art": ["n_bien", "n_esp", "n_art"],
        "bien + esp + loc": ["n_bien", "n_esp", "n_loc"],
        "bien + esp + art + loc": ["n_bien", "n_esp", "n_art", "n_loc"],
        "cab + bien + esp": ["n_cab", "n_bien", "n_esp"],
        "cab + bien + esp + art + loc": ["n_cab", "n_bien", "n_esp", "n_art", "n_loc"],
    }
    base = df[(df.estado_carga == "CDEF") & df.total_registros.notna()]
    filas = []
    for nombre, cols in candidatas.items():
        suma = base[cols].sum(axis=1)
        filas.append({"formula": nombre, "anexos_cdef": len(base),
                      "coinciden": int((suma == base.total_registros).sum()),
                      "pct_coincidencia": round(100 * (suma == base.total_registros).mean(), 2)
                      if len(base) else 0})
    tabla = pd.DataFrame(filas).sort_values("pct_coincidencia", ascending=False)
    return tabla.iloc[0].formula, tabla.assign(cols=lambda t: t.formula.map(candidatas))


def analizar(datos: dict[str, pd.DataFrame]) -> dict:
    reg = datos["registros"].copy()
    reg.columns = reg.columns.str.lower()
    reg["identificacion_informante"] = reg.identificacion_informante.astype(str).str.zfill(13)
    reg["fecha_presentacion"] = pd.to_datetime(reg.fecha_presentacion)
    reg["anio_presentacion"] = reg.fecha_presentacion.dt.year
    reg["tamanio_mb_dnrac"] = (reg.tamanio_crudo / DIVISOR_DNRAC).round(DECIMALES_DNRAC)
    reg["cero_mb"] = reg.tamanio_mb_dnrac.fillna(0) == 0
    reg["estado_desc"] = reg.estado_carga.map(ESTADOS).fillna(reg.estado_carga)

    # --- cruce con conteos de detalle
    for nombre in SQL_DETALLE:
        d = datos.get(nombre, pd.DataFrame())
        if not d.empty:
            d.columns = d.columns.str.lower()
            reg = reg.merge(d, on="codigo_registro_anexo", how="left")
    for col in ["n_cab", "n_bien", "n_bien_cdef", "n_esp", "n_esp_cdef",
                "n_art", "n_art_cdef", "n_loc", "n_loc_cdef"]:
        reg[col] = reg[col].fillna(0).astype(int) if col in reg else 0
    reg["n_detalle"] = reg[["n_bien", "n_esp", "n_art", "n_loc"]].sum(axis=1)
    reg["n_detalle_cdef"] = reg[["n_bien_cdef", "n_esp_cdef", "n_art_cdef", "n_loc_cdef"]].sum(axis=1)
    reg["clasificacion"] = reg.apply(_clasificar_detalle, axis=1)

    # --- RUC de prueba
    prueba = datos.get("prueba", pd.DataFrame()).copy()
    if not prueba.empty:
        prueba.columns = prueba.columns.str.lower()
        prueba["identificacion_informante"] = prueba.identificacion_informante.astype(str).str.zfill(13)
    sospechosos = set(prueba.identificacion_informante) if not prueba.empty else set()
    reg["es_prueba_confirmado"] = reg.identificacion_informante.isin(RUCS_PRUEBA)
    reg["es_prueba_sospechoso"] = reg.identificacion_informante.isin(sospechosos - RUCS_PRUEBA)
    reg["excluido_prueba"] = reg.es_prueba_confirmado | (
        reg.es_prueba_sospechoso & EXCLUIR_SOSPECHOSOS_PRUEBA)

    # --- fórmula de TOTAL_REGISTROS
    formula, tabla_formula = _detectar_formula(reg[~reg.excluido_prueba])
    cols_formula = tabla_formula.set_index("formula").loc[formula, "cols"]
    reg["registros_segun_formula"] = reg[cols_formula].sum(axis=1)
    reg["diferencia_total_registros"] = reg.total_registros - reg.registros_segun_formula

    # --- vigente (último CDEF por RUC y período) y caída de predios
    cdef = reg[reg.estado_carga == "CDEF"].sort_values("fecha_presentacion")
    n_cdef = cdef.groupby(["identificacion_informante", "periodo_fiscal"]).size()
    vig = cdef.groupby(["identificacion_informante", "periodo_fiscal"]).tail(1).copy()
    vig = vig.sort_values(["identificacion_informante", "periodo_fiscal"])
    vig["n_bien_periodo_anterior"] = vig.groupby("identificacion_informante").n_bien.shift(1)
    reg = reg.merge(vig[["codigo_registro_anexo", "n_bien_periodo_anterior"]],
                    on="codigo_registro_anexo", how="left")
    reg["es_vigente"] = reg.codigo_registro_anexo.isin(vig.codigo_registro_anexo)
    reg = reg.merge(n_cdef.rename("cdef_mismo_periodo").reset_index(),
                    on=["identificacion_informante", "periodo_fiscal"], how="left")

    # --- ODS
    ods = datos.get("ods", pd.DataFrame()).copy()
    hay_ods = not ods.empty
    if hay_ods:
        ods.columns = ods.columns.str.lower()
        reg = reg.merge(ods, on="codigo_registro_anexo", how="left")
        reg[["n_ods", "n_ods_original"]] = reg[["n_ods", "n_ods_original"]].fillna(0).astype(int)

    # --- anomalías
    es_cdef = reg.estado_carga == "CDEF"
    con_detalle = reg.n_bien + reg.n_esp > 0
    en_tope = pd.Series(False, index=reg.index)
    for lo, hi, _ in TOPES_EXCEL:
        for col in ["total_registros", "n_bien", "n_detalle"]:
            en_tope |= reg[col].between(lo, hi)
    reglas = {
        "A01_CERO_CON_DETALLE": es_cdef & reg.cero_mb & con_detalle,
        "A02_CERO_VACIO": es_cdef & reg.cero_mb & ~con_detalle,
        "A03_CDEF_SIN_DETALLE": es_cdef & ~reg.cero_mb & ~con_detalle,
        "A04_DETALLE_NO_CDEF": es_cdef & con_detalle & (reg.n_bien_cdef + reg.n_esp_cdef == 0),
        "A05_TOTAL_NO_CUADRA": es_cdef & reg.total_registros.notna()
                               & (reg.diferencia_total_registros != 0),
        "A06_TOPE_EXCEL": en_tope,
        "A07_CAIDA_BRUSCA": reg.es_vigente & (reg.n_bien_periodo_anterior >= CAIDA_MIN_PREVIO)
                            & (reg.n_bien <= reg.n_bien_periodo_anterior * (1 - CAIDA_UMBRAL)),
        "A08_TAMANIO_CRUDO_0": reg.tamanio_crudo.fillna(0) == 0,
        "A09_FALLIDO_CON_DETALLE": reg.estado_carga.isin(["FAL", "SUS"]) & (reg.n_detalle > 0),
        "A10_CDEF_MULTIPLE": es_cdef & (reg.cdef_mismo_periodo > 1),
    }
    if hay_ods:
        reglas["A11_ODS_NO_CUADRA"] = es_cdef & (reg.n_ods_original != reg.n_bien_cdef)
        reglas["A12_ODS_DUPLICADO"] = reg.n_ods > reg.n_ods_original
    for cod, mask in reglas.items():
        reg[cod] = mask.fillna(False)
    cods = list(reglas)
    reg["anomalias"] = reg[cods].apply(lambda r: ", ".join(c[:3] for c in cods if r[c]), axis=1)
    reg["n_anomalias"] = reg[cods].sum(axis=1)

    return {"reg": reg, "tabla_formula": tabla_formula.drop(columns="cols"), "formula": formula,
            "prueba": prueba, "codigos": cods, "hay_ods": hay_ods}


# ==========================================================================
# RESÚMENES
# ==========================================================================
def resumenes(res: dict) -> dict[str, pd.DataFrame]:
    reg = res["reg"]
    val = reg[~reg.excluido_prueba]
    cero = val[val.cero_mb]

    def pct(a, b):
        return round(100 * a / b, 1) if b else 0.0

    total, total_cero = len(val), len(cero)
    cdef, cdef_cero = (val.estado_carga == "CDEF").sum(), (cero.estado_carga == "CDEF").sum()
    cero_cdef = cero[cero.estado_carga == "CDEF"]
    con_det = (cero_cdef.n_bien + cero_cdef.n_esp > 0).sum()

    cifras = pd.DataFrame([
        ("Anexos presentados (sin prueba)", total, ""),
        ("Anexos excluidos por ser de prueba", int(reg.excluido_prueba.sum()),
         f"{reg[reg.excluido_prueba].identificacion_informante.nunique()} RUC"),
        ("Anexos con 0 MB (todos los estados)", total_cero, f"{pct(total_cero, total)} %"),
        ("Anexos CDEF", int(cdef), ""),
        ("Anexos CDEF con 0 MB", int(cdef_cero), f"{pct(cdef_cero, cdef)} % de los CDEF"),
        ("   ... con detalle grabado", int(con_det), f"{pct(con_det, cdef_cero)} % de los CDEF 0 MB"),
        ("   ... sin detalle (vacío real)", int(cdef_cero - con_det),
         f"{pct(cdef_cero - con_det, cdef_cero)} % de los CDEF 0 MB"),
        ("Predios grabados en anexos CDEF 0 MB", int(cero_cdef.n_bien.sum()), ""),
        ("Espectáculos grabados en anexos CDEF 0 MB", int(cero_cdef.n_esp.sum()), ""),
        ("Tamaño crudo máximo de un anexo 0 MB", float(cero.tamanio_crudo.max() or 0), UNIDAD_CRUDA),
        ("Fórmula que reproduce TOTAL_REGISTROS", res["formula"],
         f"{res['tabla_formula'].iloc[0].pct_coincidencia} % de coincidencia"),
    ], columns=["indicador", "valor", "detalle"])

    por_estado = (val.groupby(["anio_presentacion", "estado_carga"])
                  .agg(anexos=("codigo_registro_anexo", "size"), cero_mb=("cero_mb", "sum"))
                  .reset_index())
    por_estado["pct_cero"] = (100 * por_estado.cero_mb / por_estado.anexos).round(1)

    cero_clasif = (cero.groupby(["estado_carga", "clasificacion"])
                   .agg(anexos=("codigo_registro_anexo", "size"), predios=("n_bien", "sum"),
                        espectaculos=("n_esp", "sum"), artistas=("n_art", "sum"),
                        localidades=("n_loc", "sum"))
                   .reset_index())

    anomalias = pd.DataFrame([
        {"codigo": c, "descripcion": CATALOGO_ANOMALIAS[c], "anexos": int(val[c].sum()),
         "gad_distintos": int(val.loc[val[c], "identificacion_informante"].nunique())}
        for c in res["codigos"]])

    por_gad = (val.groupby("identificacion_informante")
               .agg(anexos=("codigo_registro_anexo", "size"),
                    anexos_cero=("cero_mb", "sum"),
                    cdef_cero_vacios=("A02_CERO_VACIO", "sum"),
                    cdef_cero_con_detalle=("A01_CERO_CON_DETALLE", "sum"),
                    periodos=("periodo_fiscal", "nunique"),
                    predios_total=("n_bien", "sum"),
                    anomalias=("n_anomalias", "sum"))
               .reset_index()
               .sort_values(["cdef_cero_vacios", "anexos_cero"], ascending=False))

    return {"cifras": cifras, "por_estado": por_estado, "cero_clasif": cero_clasif,
            "anomalias": anomalias, "por_gad": por_gad}


# ==========================================================================
# EXCEL
# ==========================================================================
COLS_LISTADO = [
    "codigo_registro_anexo", "identificacion_informante", "periodo_fiscal", "estado_carga",
    "estado_desc", "fecha_presentacion", "tamanio_crudo", "tamanio_mb_dnrac", "total_registros",
    "registros_segun_formula", "diferencia_total_registros", "clasificacion",
    "n_cab", "n_bien", "n_bien_cdef", "n_esp", "n_esp_cdef", "n_art", "n_loc",
    "n_bien_periodo_anterior", "es_vigente", "es_prueba_sospechoso", "anomalias",
]


def escribir_excel(res: dict, rs: dict, ruta: Path):
    reg = res["reg"]
    val = reg[~reg.excluido_prueba]
    cols = COLS_LISTADO + (["n_ods", "n_ods_original"] if res["hay_ods"] else [])
    cero = val[val.cero_mb].sort_values(["estado_carga", "n_detalle"], ascending=[True, False])
    top = (val[val.n_anomalias > 0]
           .assign(_cero=lambda d: d.cero_mb.astype(int))
           .sort_values(["A02_CERO_VACIO", "_cero", "n_anomalias", "n_detalle"],
                        ascending=False)
           .head(TOP_N))

    hojas = {
        "Resumen": rs["cifras"],
        "Por_estado_anio": rs["por_estado"],
        "Cero_por_clasificacion": rs["cero_clasif"],
        "Anomalias_resumen": rs["anomalias"],
        "Cero_MB_todos": cero[cols],
        "CDEF_cero_con_detalle": val[val.A01_CERO_CON_DETALLE][cols],
        "CDEF_cero_vacios": val[val.A02_CERO_VACIO][cols],
        f"Top_{TOP_N}_revisar": top[cols],
        "Por_GAD": rs["por_gad"],
        "Formula_total_registros": res["tabla_formula"],
        "Posibles_prueba": (reg[reg.es_prueba_confirmado | reg.es_prueba_sospechoso][cols]),
        "Catalogo_anomalias": pd.DataFrame(CATALOGO_ANOMALIAS.items(),
                                           columns=["codigo", "descripcion"]),
    }
    for c in res["codigos"]:
        sub = val[val[c]]
        if len(sub) and c not in ("A01_CERO_CON_DETALLE", "A02_CERO_VACIO"):
            hojas[c[:31]] = sub[cols]

    with pd.ExcelWriter(ruta, engine="openpyxl") as xw:
        for nombre, df in hojas.items():
            df.to_excel(xw, sheet_name=nombre[:31], index=False)
            ws = xw.sheets[nombre[:31]]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for i, col in enumerate(df.columns, start=1):
                largo = max([len(str(col))] + [len(str(v)) for v in df[col].head(200)])
                ws.column_dimensions[ws.cell(1, i).column_letter].width = min(max(10, largo + 2), 60)
    log.info("Excel: %s", ruta.resolve())


# ==========================================================================
# HTML + GRÁFICAS
# ==========================================================================
SERIE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
TINTA, TINTA2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def _fig_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="white")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _estilo(ax, titulo: str):
    ax.set_title(titulo, loc="left", fontsize=11, color=TINTA, pad=10)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=TINTA2, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def graficas(res: dict, rs: dict) -> dict[str, str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    reg = res["reg"]
    val = reg[~reg.excluido_prueba]
    g = {}

    # 1. % de anexos 0 MB por año de presentación y estado
    pe = rs["por_estado"]
    estados = [e for e in ["CDEF", "FAL", "SUS", "RIDE", "CAR", "VAL"] if e in set(pe.estado_carga)]
    anios = sorted(pe.anio_presentacion.unique())
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ancho = 0.8 / max(len(estados), 1)
    for i, e in enumerate(estados):
        sub = pe[pe.estado_carga == e].set_index("anio_presentacion").reindex(anios)
        xs = [a + (i - (len(estados) - 1) / 2) * ancho for a in anios]
        ax.bar(xs, sub.cero_mb.fillna(0), width=ancho * 0.92, color=SERIE[i], label=ESTADOS.get(e, e))
    ax.set_xticks(anios)
    ax.set_ylabel("anexos con 0 MB", color=TINTA2, fontsize=9)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.18)
    ax.legend(frameon=False, fontsize=8, ncol=len(estados), loc="upper right")
    _estilo(ax, "Anexos con 0 MB por año de presentación y estado")
    g["estado_anio"] = _fig_b64(fig)

    # 2. Tamaño crudo de los 0 MB (demuestra que es redondeo, no vacío)
    cero = val[val.cero_mb]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    datos = cero.tamanio_crudo.dropna()
    if len(datos):
        ax.hist(datos, bins=min(26, max(5, datos.nunique())), color=SERIE[0],
                edgecolor="white", linewidth=1.5)
    ax.axvline(DIVISOR_DNRAC * 0.005, color=TINTA2, linestyle="--", linewidth=1)
    ax.text(DIVISOR_DNRAC * 0.005, ax.get_ylim()[1] * 0.92, "  límite del redondeo a 0,00",
            color=TINTA2, fontsize=8)
    ax.set_xlabel(f"tamaño crudo TAMANIO_ARCHIVO_ANEXO ({UNIDAD_CRUDA})", color=TINTA2, fontsize=9)
    ax.set_ylabel("anexos", color=TINTA2, fontsize=9)
    _estilo(ax, "Tamaño real de los anexos que la DNRAC ve como 0 MB")
    g["tamanio"] = _fig_b64(fig)

    # 3. Qué tienen grabado los CDEF 0 MB
    cc = (val[val.cero_mb & (val.estado_carga == "CDEF")].clasificacion.value_counts().sort_index())
    fig, ax = plt.subplots(figsize=(8, 2.8))
    if len(cc):
        colores = [SERIE[7] if k.startswith(("1", "2")) else SERIE[2] for k in cc.index]
        barras = ax.barh(cc.index[::-1], cc.values[::-1], color=colores[::-1], height=0.6)
        ax.bar_label(barras, padding=4, fontsize=9, color=TINTA)
    ax.grid(axis="x", color=GRID)
    ax.grid(axis="y", visible=False)
    _estilo(ax, "Anexos CDEF con 0 MB: qué quedó grabado en RIG")
    ax.grid(axis="y", visible=False)
    g["clasif"] = _fig_b64(fig)

    # 4. TOTAL_REGISTROS vs detalle grabado
    c = val[val.estado_carga == "CDEF"]
    fig, ax = plt.subplots(figsize=(5.5, 4.2))
    ax.scatter(c.registros_segun_formula.clip(lower=0.8), c.total_registros.clip(lower=0.8),
               s=14, alpha=0.6, color=SERIE[0], edgecolors="white", linewidths=0.6)
    lim = max(c.registros_segun_formula.max() or 1, c.total_registros.max() or 1) * 1.2
    ax.plot([0.8, lim], [0.8, lim], color=TINTA2, linewidth=1, linestyle="--")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(f"grabado en detalle ({res['formula']})", color=TINTA2, fontsize=9)
    ax.set_ylabel("TOTAL_REGISTROS", color=TINTA2, fontsize=9)
    _estilo(ax, "TOTAL_REGISTROS vs detalle grabado (CDEF)")
    g["formula"] = _fig_b64(fig)

    # 5. Anomalías
    an = rs["anomalias"].query("anexos > 0").sort_values("anexos")
    fig, ax = plt.subplots(figsize=(8, max(2.4, 0.42 * len(an) + 0.8)))
    if len(an):
        barras = ax.barh(an.codigo, an.anexos, color=SERIE[0], height=0.6)
        ax.bar_label(barras, padding=4, fontsize=9, color=TINTA)
    _estilo(ax, "Anexos por tipo de anomalía (sin RUC de prueba)")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID)
    g["anomalias"] = _fig_b64(fig)
    return g


def _tabla_html(df: pd.DataFrame, max_filas: int = 25) -> str:
    df = df.head(max_filas).copy()
    for c in df.select_dtypes("datetime"):
        df[c] = df[c].dt.strftime("%Y-%m-%d %H:%M")
    return df.to_html(index=False, border=0, classes="tabla", na_rep="", escape=True)


def razones(res: dict, rs: dict) -> list[str]:
    """Texto de justificación construido con las cifras reales."""
    reg = res["reg"]
    val = reg[~reg.excluido_prueba]
    cero = val[val.cero_mb]
    cdef_cero = cero[cero.estado_carga == "CDEF"]
    vacios = cdef_cero[cdef_cero.n_bien + cdef_cero.n_esp == 0]
    con_det = cdef_cero[cdef_cero.n_bien + cdef_cero.n_esp > 0]
    lim_kb = DIVISOR_DNRAC * 0.005
    max_cero = cero.tamanio_crudo.max()
    tf = res["tabla_formula"].iloc[0]
    out = [
        f"<b>El “0 MB” es un efecto del redondeo.</b> La DNRAC calcula el peso como "
        f"round(TAMANIO_ARCHIVO_ANEXO/{DIVISOR_DNRAC}, {DECIMALES_DNRAC}); cualquier archivo menor a "
        f"{lim_kb:.2f} {UNIDAD_CRUDA} se muestra como 0. El mayor anexo “0 MB” pesa realmente "
        f"{0 if pd.isna(max_cero) else max_cero:,.2f} {UNIDAD_CRUDA}, y solo "
        f"{int((cero.tamanio_crudo.fillna(0) == 0).sum())} tienen tamaño crudo exactamente 0.",
        f"<b>De {len(cdef_cero):,} anexos CDEF con 0 MB, {len(con_det):,} sí tienen detalle grabado</b> "
        f"en RIG ({int(con_det.n_bien.sum()):,} predios y {int(con_det.n_esp.sum()):,} espectáculos); "
        f"<b>{len(vacios):,} están realmente vacíos</b> "
        f"({(vacios.clasificacion == '2. Solo cabecera').sum():,} solo con cabecera y "
        f"{(vacios.clasificacion == '1. Sin cabecera').sum():,} sin cabecera).",
        f"<b>Los estados no CDEF no cuentan como presentación válida:</b> de {len(cero):,} anexos 0 MB, "
        f"{len(cero) - len(cdef_cero):,} son FAL/SUS/RIDE u otros. El porcentaje del memo depende de "
        f"si se usan todas las presentaciones o solo las CDEF.",
        f"<b>TOTAL_REGISTROS</b> coincide con <i>{tf.formula}</i> en el {tf.pct_coincidencia} % de los CDEF; "
        f"{int(val.A05_TOTAL_NO_CUADRA.sum()):,} anexos no cuadran y se listan en el Excel.",
        f"Se excluyeron {reg[reg.excluido_prueba].identificacion_informante.nunique()} RUC de prueba "
        f"({int(reg.excluido_prueba.sum())} anexos).",
        "Desde el período 2022 la norma pide reportar solo bienes inmuebles nuevos o actualizados, "
        "por lo que es esperable que GAD pequeños presenten archivos de pocos predios (pocos KB).",
    ]
    if res["hay_ods"]:
        out.append(f"<b>ODS:</b> {int(val.A12_ODS_DUPLICADO.sum()):,} anexos tienen copias del arrastre "
                   f"insertadas en el mismo año (bug del paso 4 de BOD_PRO_CARGA_INICIAL_BIEN: usa ANIO "
                   f"en vez de REGISTRO.DESTINO). Contar desde el ODS sobreestima los predios.")
    return out


def escribir_html(res: dict, rs: dict, g: dict, ruta: Path):
    reg = res["reg"]
    val = reg[~reg.excluido_prueba]
    cdef_cero = val[val.cero_mb & (val.estado_carga == "CDEF")]
    con_det = int((cdef_cero.n_bien + cdef_cero.n_esp > 0).sum())
    vacios = len(cdef_cero) - con_det
    kpis = [
        ("Anexos 0 MB", f"{int(val.cero_mb.sum()):,}", "todos los estados, sin prueba"),
        ("CDEF con 0 MB", f"{len(cdef_cero):,}", "carga definitiva"),
        ("Con detalle grabado", f"{con_det:,}", "el 0 MB es redondeo"),
        ("Vacíos reales", f"{vacios:,}", "sin inmuebles ni espectáculos"),
    ]
    img = lambda k, alt: f'<img src="data:image/png;base64,{g[k]}" alt="{html.escape(alt)}">'
    top_vacios = val[val.A02_CERO_VACIO][["identificacion_informante", "periodo_fiscal",
                                         "fecha_presentacion", "tamanio_crudo", "total_registros",
                                         "clasificacion"]]
    doc = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Anexos GAD 0 MB</title>
<style>
:root {{ color-scheme: light; --bg:#f6f5f2; --card:#fcfcfb; --tx:#0b0b0b; --tx2:#52514e;
        --line:#e4e3df; --acc:#2a78d6; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--tx);
       font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
main {{ max-width:1040px; margin:0 auto; padding:32px 16px 64px; }}
h1 {{ font-size:26px; margin:0 0 4px; }} h2 {{ font-size:18px; margin:36px 0 12px; }}
.sub {{ color:var(--tx2); margin:0 0 24px; }}
.kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; }}
.kpi {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }}
.kpi b {{ display:block; font-size:28px; font-variant-numeric:tabular-nums; }}
.kpi span {{ color:var(--tx2); font-size:13px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px;
        margin-bottom:14px; overflow-x:auto; }}
.card img {{ max-width:100%; height:auto; display:block; }}
ol li {{ margin-bottom:8px; }}
table.tabla {{ border-collapse:collapse; font-size:13px; width:100%; }}
.tabla th {{ text-align:left; color:var(--tx2); font-weight:600; border-bottom:1px solid var(--line);
            padding:6px 8px; white-space:nowrap; }}
.tabla td {{ border-bottom:1px solid var(--line); padding:6px 8px; font-variant-numeric:tabular-nums; }}
footer {{ color:var(--tx2); font-size:12px; margin-top:40px; }}
</style></head><body><main>
<h1>Anexos GAD con peso “0 MB”</h1>
<p class="sub">Seguimiento al memo DNRAC · presentaciones {ANIO_DESDE}–{ANIO_HASTA} ·
generado {datetime.now():%Y-%m-%d %H:%M} · fuente RIG@db_sri</p>

<div class="kpis">{"".join(f'<div class="kpi"><span>{t}</span><b>{v}</b><span>{s}</span></div>'
                             for t, v, s in kpis)}</div>

<h2>Conclusiones</h2>
<div class="card"><ol>{"".join(f"<li>{r}</li>" for r in razones(res, rs))}</ol></div>

<h2>¿Por qué aparecen en 0?</h2>
<div class="card">{img("tamanio", "Histograma del tamaño crudo")}</div>
<div class="card">{img("estado_anio", "Anexos 0 MB por año y estado")}</div>

<h2>¿Qué grabó el sistema?</h2>
<div class="card">{img("clasif", "Clasificación de los CDEF 0 MB")}</div>
<div class="card"><div style="max-width:560px">{img("formula", "TOTAL_REGISTROS vs detalle")}</div></div>
<div class="card">{_tabla_html(rs["cero_clasif"])}</div>

<h2>Anomalías detectadas</h2>
<div class="card">{img("anomalias", "Anomalías por tipo")}</div>
<div class="card">{_tabla_html(rs["anomalias"], 50)}</div>

<h2>Anexos CDEF realmente vacíos (primeros 25)</h2>
<div class="card">{_tabla_html(top_vacios) if len(top_vacios) else "<p>No hay ninguno.</p>"}</div>

<h2>Cifras</h2>
<div class="card">{_tabla_html(rs["cifras"], 50)}</div>

<footer>El detalle completo (todos los anexos, top {TOP_N} a revisar y una hoja por anomalía)
está en el Excel generado junto a este reporte.</footer>
</main></body></html>"""
    ruta.write_text(doc, encoding="utf-8")
    log.info("HTML: %s", ruta.resolve())


# ==========================================================================
# MAIN
# ==========================================================================
def main():
    ap = argparse.ArgumentParser(description="Análisis de anexos GAD con 0 MB")
    ap.add_argument("--desde-csv", type=Path, help="carpeta con extractos CSV (no usa BD)")
    ap.add_argument("--guardar-csv", action="store_true", help="guarda los extractos en salida/extractos")
    args = ap.parse_args()

    DIR_SALIDA.mkdir(parents=True, exist_ok=True)
    if args.desde_csv:
        datos = leer_csv(args.desde_csv)
    else:
        datos = extraer_bd()
        if args.guardar_csv:
            guardar_csv(datos, DIR_SALIDA / "extractos")
    if datos["registros"].empty:
        sys.exit("No hay registros que analizar")

    res = analizar(datos)
    rs = resumenes(res)
    sello = datetime.now().strftime("%Y%m%d_%H%M")
    escribir_excel(res, rs, DIR_SALIDA / f"analisis_gad_cero_mb_{sello}.xlsx")
    escribir_html(res, rs, graficas(res, rs), DIR_SALIDA / f"reporte_gad_cero_mb_{sello}.html")
    print(rs["cifras"].to_string(index=False))


if __name__ == "__main__":
    main()
