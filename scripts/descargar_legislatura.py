#!/usr/bin/env python3
"""
Descarga todas las votaciones del Pleno de la XV Legislatura.

Itera día a día (solo días laborables) desde el inicio de la legislatura
hasta hoy, consulta el opendata del Congreso con targetDate=DD/MM/AAAA,
y procesa las votaciones encontradas.

Uso:
    # Descarga completa (puede tardar varias horas):
    python scripts/descargar_legislatura.py

    # Solo a partir de una fecha concreta (para reanudar):
    python scripts/descargar_legislatura.py --desde 01/01/2025

    # Hasta una fecha concreta:
    python scripts/descargar_legislatura.py --hasta 31/12/2024

    # Solo N sesiones (para pruebas):
    python scripts/descargar_legislatura.py --max-sesiones 3

    # Guardar en ruta distinta:
    python scripts/descargar_legislatura.py --out data/legislatura.csv

Las sesiones ya procesadas se saltan automáticamente (deduplicación por
sesion+num_votacion en el CSV de salida).
"""

import argparse
import sys
import time
from datetime import date, timedelta

import sesiones
import votaciones
import expedientes
import orden_dia
import grupos
import bocg
import csv_io

# XV Legislatura: primera sesión plenaria
INICIO_LEGISLATURA = date(2023, 8, 17)

# Pausa entre sesiones para no saturar el servidor (segundos)
PAUSA_ENTRE_SESIONES = 2.0
# Pausa entre días sin sesión
PAUSA_ENTRE_DIAS = 0.3


def ya_procesadas(ruta_csv: str) -> set[tuple]:
    """Lee el CSV y devuelve el conjunto de (sesion, num_votacion) ya escritas."""
    filas = csv_io.leer_todo(ruta_csv)
    return {csv_io.clave_unica(f) for f in filas}


def procesar_votacion(item: dict, items_oda: list[dict]) -> list[dict]:
    """Reutiliza la lógica de main.py para procesar una votación."""
    datos = item["datos"]
    info  = datos["informacion"]
    tot   = datos["totales"]

    oda_item = orden_dia.buscar_expediente(info.get("textoExpediente", ""), items_oda)
    meta = expedientes.clasificar(info, orden_dia_item=oda_item)

    posiciones = grupos.agregar(datos["votaciones"])

    bocg_result = bocg.descargar_texto(meta["bocg_url"])
    texto_relevante = bocg.extraer_parte_relevante(bocg_result["texto"], meta["tipo"])

    resultado = "Aprobada" if tot["afavor"] > tot["enContra"] else "Rechazada"

    fila = {
        "fecha":                 item["fecha"],
        "sesion":                item["sesion"],
        "num_votacion":          item["num_votacion"],
        "expediente":            meta["expediente"] or "",
        "tipo":                  meta["tipo"],
        "punto":                 meta["punto"] or "",
        "titulo":                "",
        "resumen":               "",
        "grupo_inicia":          meta["grupo_inicia"] or "",
        "es_enmienda_totalidad": str(meta["es_enmienda_totalidad"]),
        "resultado":             resultado,
        "si_total":              tot["afavor"],
        "no_total":              tot["enContra"],
        "abs_total":             tot["abstenciones"],
        "PP_voto":     posiciones.get("PP", ""),
        "PSOE_voto":   posiciones.get("PSOE", ""),
        "Vox_voto":    posiciones.get("Vox", ""),
        "Sumar_voto":  posiciones.get("Sumar", ""),
        "ERC_voto":    posiciones.get("ERC", ""),
        "Junts_voto":  posiciones.get("Junts", ""),
        "Bildu_voto":  posiciones.get("Bildu", ""),
        "PNV_voto":    posiciones.get("PNV", ""),
        "MxSUMAR_voto": posiciones.get("MxSUMAR", ""),
        "MxBNG_voto":   posiciones.get("MxBNG", ""),
        "MxCCa_voto":   posiciones.get("MxCCa", ""),
        "MxUPN_voto":   posiciones.get("MxUPN", ""),
        "MxVOX_voto":   posiciones.get("MxVOX", ""),
        "_texto_bocg":  texto_relevante,
        "_bocg_fuente": bocg_result["fuente"],
        "_texto_exp":   info.get("textoExpediente", ""),
    }
    return [fila]


def fecha_a_ddmmaaaa(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def main():
    parser = argparse.ArgumentParser(
        description="Descarga todas las votaciones de la XV Legislatura"
    )
    parser.add_argument(
        "--desde", default=None, metavar="DD/MM/AAAA",
        help="Fecha de inicio (inclusive). Por defecto: inicio de legislatura"
    )
    parser.add_argument(
        "--hasta", default=None, metavar="DD/MM/AAAA",
        help="Fecha de fin (inclusive). Por defecto: hoy"
    )
    parser.add_argument(
        "--max-sesiones", type=int, default=None,
        help="Detener tras procesar N sesiones (para pruebas)"
    )
    parser.add_argument(
        "--out", default="data/votaciones.csv",
        help="Ruta del CSV de salida (default: data/votaciones.csv)"
    )
    parser.add_argument(
        "--pausa", type=float, default=PAUSA_ENTRE_SESIONES,
        help=f"Segundos entre sesiones (default: {PAUSA_ENTRE_SESIONES})"
    )
    args = parser.parse_args()

    # Rango de fechas
    def parse_fecha(s: str) -> date:
        d, m, y = s.split("/")
        return date(int(y), int(m), int(d))

    fecha_inicio = parse_fecha(args.desde) if args.desde else INICIO_LEGISLATURA
    fecha_fin    = parse_fecha(args.hasta) if args.hasta else date.today()

    print(f"Rango: {fecha_inicio} → {fecha_fin}")
    print(f"CSV de salida: {args.out}")

    # Cargar sesiones ya procesadas para deduplicar
    procesadas = ya_procesadas(args.out)
    print(f"Votaciones ya en CSV: {len(procesadas)}\n")

    sesiones_procesadas = 0
    filas_totales = 0
    dia = fecha_inicio

    while dia <= fecha_fin:
        # Solo días laborables (lun–vie); el Congreso no plena en fin de semana
        if dia.weekday() >= 5:
            dia += timedelta(days=1)
            continue

        fecha_str = fecha_a_ddmmaaaa(dia)
        items = sesiones.obtener_sesion_por_fecha(fecha_str)

        if not items:
            time.sleep(PAUSA_ENTRE_DIAS)
            dia += timedelta(days=1)
            continue

        sesion_num = items[0]["sesion"]
        fecha_yyyymmdd = items[0]["fecha"]
        print(f"[{fecha_str}] Sesión {sesion_num} — {len(items)} votaciones")

        # Comprobar si todas las votaciones de esta sesión ya están procesadas
        claves_sesion = {(str(it["sesion"]), str(it["num_votacion"])) for it in items}
        if claves_sesion <= procesadas:
            print(f"  Ya procesada, saltando.")
            dia += timedelta(days=1)
            continue

        # Orden del día
        items_oda = orden_dia.descargar_orden_dia(fecha_yyyymmdd, sesion_num)
        if items_oda:
            print(f"  Orden del día: {len(items_oda)} items")
        else:
            print(f"  Orden del día no disponible — usando detección por texto")

        # Descargar JSONs
        items_con_datos = votaciones.descargar_todas(items)

        # Procesar y escribir
        filas_sesion = 0
        for item in items_con_datos:
            clave = (str(item["sesion"]), str(item["num_votacion"]))
            if clave in procesadas:
                continue  # ya en CSV, saltar

            try:
                filas = procesar_votacion(item, items_oda)
            except Exception as e:
                print(f"  ERROR votación {item['num_votacion']}: {e}")
                continue

            for fila in filas:
                fila_csv = {k: v for k, v in fila.items() if not k.startswith("_")}
                csv_io.escribir_fila(fila_csv, args.out)
                procesadas.add(csv_io.clave_unica(fila_csv))
                filas_sesion += 1
                filas_totales += 1

        print(f"  → {filas_sesion} filas escritas  (total acumulado: {filas_totales})")
        sesiones_procesadas += 1

        if args.max_sesiones and sesiones_procesadas >= args.max_sesiones:
            print(f"\nLímite de {args.max_sesiones} sesiones alcanzado.")
            break

        time.sleep(args.pausa)
        dia += timedelta(days=1)

    print(f"\n✓ Fin. {sesiones_procesadas} sesiones procesadas, {filas_totales} filas nuevas.")
    print(f"  CSV: {args.out}")
    if filas_totales > 0:
        print(f"  Para generar títulos y resúmenes:")
        print(f"  python scripts/generar_resumenes.py --csv {args.out}")


if __name__ == "__main__":
    main()
