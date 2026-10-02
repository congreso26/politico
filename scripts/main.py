#!/usr/bin/env python3
"""
Herramienta para generar la base de datos de votaciones del Pleno del Congreso.

Uso:
    # Procesar la sesión más reciente (automático):
    python scripts/main.py

    # Procesar sesión pasada con URLs manuales (copiar URLs del navegador):
    python scripts/main.py --urls URL1 URL2 URL3 ...

    # Procesar solo N votaciones (útil para pruebas):
    python scripts/main.py --limit 3

    # Guardar en ruta distinta:
    python scripts/main.py --out data/prueba.csv

El script descarga los datos, extrae el texto del BOCG y escribe una fila
por votación (o por punto si una iniciativa se vota por puntos).

Los campos 'titulo' y 'resumen' se dejan vacíos para rellenar manualmente
con ayuda del LLM a partir del texto_bocg.
"""

import argparse
import json
import sys

import sesiones
import votaciones
import expedientes
import orden_dia
import grupos
import bocg
import csv_io


def procesar_votacion(item: dict, items_oda: list[dict]) -> list[dict]:
    """
    Procesa una votación descargada y devuelve una o más filas (una por punto).

    item = {"sesion", "fecha", "num_votacion", "url", "datos": {...}}
    """
    datos = item["datos"]
    info  = datos["informacion"]
    tot   = datos["totales"]

    # Buscar expediente en el orden del día y clasificar
    oda_item = orden_dia.buscar_expediente(info.get("textoExpediente", ""), items_oda)
    meta = expedientes.clasificar(info, orden_dia_item=oda_item)

    # Agregar votos por grupo
    posiciones = grupos.agregar(datos["votaciones"])

    # Descargar texto BOCG
    bocg_result = bocg.descargar_texto(meta["bocg_url"])
    texto_relevante = bocg.extraer_parte_relevante(bocg_result["texto"], meta["tipo"])

    # Resultado global
    resultado = "Aprobada" if tot["afavor"] > tot["enContra"] else "Rechazada"

    # Construir fila base
    fila = {
        "fecha":                 item["fecha"],
        "sesion":                item["sesion"],
        "num_votacion":          item["num_votacion"],
        "expediente":            meta["expediente"] or "",
        "tipo":                  meta["tipo"],
        "punto":                 meta["punto"] or "",
        "titulo":                "",   # rellenar manualmente
        "resumen":               "",   # rellenar manualmente
        "grupo_inicia":          meta["grupo_inicia"] or "",
        "es_enmienda_totalidad": str(meta["es_enmienda_totalidad"]),
        "resultado":             resultado,
        "si_total":              tot["afavor"],
        "no_total":              tot["enContra"],
        "abs_total":             tot["abstenciones"],
        # Votos por grupo
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
        # Campo extra para ayudar al LLM a generar título/resumen (no en COLUMNAS del CSV)
        "_texto_bocg":   texto_relevante,
        "_bocg_fuente":  bocg_result["fuente"],
        "_texto_exp":    info.get("textoExpediente", ""),
    }

    return [fila]


def imprimir_resumen(fila: dict) -> None:
    """Imprime un resumen legible de la votación procesada."""
    print(f"\n  Votación {fila['num_votacion']:03d} — {fila['tipo'].upper()} {fila['expediente']}")
    if fila["punto"]:
        print(f"    Punto: {fila['punto']}")
    print(f"    Propone: {fila['grupo_inicia']}  |  {fila['resultado']}  "
          f"({fila['si_total']} sí / {fila['no_total']} no / {fila['abs_total']} abst.)")

    grupos_pos = {}
    for col in csv_io.COLUMNAS:
        if col.endswith("_voto") and fila.get(col):
            grupos_pos.setdefault(fila[col], []).append(col.replace("_voto", ""))
    for pos in ("A favor", "En contra", "Abstención", "Dividido"):
        if pos in grupos_pos:
            print(f"    {pos:12s}: {', '.join(grupos_pos[pos])}")

    fuente = fila.get("_bocg_fuente", "")
    if fuente == "bocg":
        preview = fila.get("_texto_bocg", "")[:120].replace("\n", " ")
        print(f"    BOCG: {preview}…")
    else:
        print(f"    BOCG: {fuente}")


def main():
    parser = argparse.ArgumentParser(
        description="Genera CSV de votaciones del Pleno del Congreso"
    )
    parser.add_argument(
        "--urls", nargs="+", metavar="URL",
        help="URLs de JSON de votación (modo manual para sesiones pasadas)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Procesar solo las primeras N votaciones"
    )
    parser.add_argument(
        "--out", default="data/votaciones.csv",
        help="Ruta del CSV de salida (default: data/votaciones.csv)"
    )
    args = parser.parse_args()

    # 1. Descubrir URLs de la sesión
    if args.urls:
        print(f"Modo manual: {len(args.urls)} URLs proporcionadas.")
        items = sesiones.desde_urls(args.urls)
    else:
        print("Obteniendo sesión actual del índice de opendata...")
        items = sesiones.obtener_sesion_actual()
        if not items:
            print("No se encontraron votaciones en el índice.")
            sys.exit(1)
        print(f"Sesión {items[0]['sesion']} ({items[0]['fecha']}) — {len(items)} votaciones.")

    if args.limit:
        items = items[:args.limit]
        print(f"Limitado a {args.limit} votaciones.")

    # 2. Descargar orden del día (para obtener expedientes y BOCG)
    sesion_num = items[0]["sesion"]
    fecha      = items[0]["fecha"]
    print(f"\nDescargando orden del día (sesión {sesion_num}, {fecha})...")
    items_oda = orden_dia.descargar_orden_dia(fecha, sesion_num)
    if items_oda:
        print(f"  {len(items_oda)} items encontrados en el orden del día.")
    else:
        print("  No disponible — se usará detección por texto.")

    # 3. Descargar JSONs de votaciones
    print("\nDescargando JSONs de votaciones...")
    items_con_datos = votaciones.descargar_todas(items)

    # 4. Procesar y escribir
    print(f"\nProcesando y escribiendo en {args.out}...\n")
    filas_escritas = 0
    for item in items_con_datos:
        filas = procesar_votacion(item, items_oda)
        for fila in filas:
            imprimir_resumen(fila)
            # Escribir sin los campos _ (metadatos internos)
            fila_csv = {k: v for k, v in fila.items() if not k.startswith("_")}
            csv_io.escribir_fila(fila_csv, args.out)
            filas_escritas += 1

    print(f"\n✓ {filas_escritas} filas escritas en {args.out}")
    print(f"  Para generar títulos y resúmenes, ejecuta desde aquí:")
    print(f"  python scripts/generar_resumenes.py --csv {args.out}")


if __name__ == "__main__":
    main()
