#!/usr/bin/env python3
"""
Genera data/textos.csv con el texto fuente de cada votación.

Columnas: fecha, sesion, num_votacion, texto_exp, texto_bocg, bocg_fuente

- texto_exp:  textoExpediente del JSON de votación (descripción de la iniciativa)
- texto_bocg: texto extraído del PDF del BOCG (cuando hay expediente)
- bocg_fuente: "bocg" | "no_disponible" | "error_404" | "error_otro"

Se enlaza con votaciones.csv mediante (fecha, sesion, num_votacion).

Uso:
    python scripts/descargar_textos.py
    python scripts/descargar_textos.py --desde 20260901   # reanudar
    python scripts/descargar_textos.py --out data/textos.csv
"""

import argparse
import csv
import time
import urllib.request
from pathlib import Path

import sesiones as sesiones_mod
import bocg
import expedientes as exp_mod

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; scraper-congreso/1.0)"}
COLUMNAS = ["fecha", "sesion", "num_votacion", "texto_exp", "texto_bocg", "bocg_fuente"]
PAUSA = 0.5  # segundos entre JSONs de votación


def _fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        import json
        return json.loads(resp.read())


def _bocg_url_desde_csv(row: dict) -> str | None:
    """Reconstruye bocg_url a partir de expediente+tipo del CSV."""
    expediente = row.get("expediente", "")
    tipo = row.get("tipo", "")
    if not expediente:
        return None
    _, _, parte = expediente.partition("/")
    try:
        num = str(int(parte))
    except ValueError:
        return None
    plantillas = {
        "PNL":             "https://www.congreso.es/public_oficiales/L15/CONG/BOCG/D/BOCG-15-D-{n}.PDF",
        "proyecto_ley":    "https://www.congreso.es/public_oficiales/L15/CONG/BOCG/A/BOCG-15-A-{n}-1.PDF",
        "proposicion_ley": "https://www.congreso.es/public_oficiales/L15/CONG/BOCG/B/BOCG-15-B-{n}-1.PDF",
        "convenio":        "https://www.congreso.es/public_oficiales/L15/CORT/BOCG/A/BOCG-15-CG-A-{n}.PDF",
    }
    plantilla = plantillas.get(tipo)
    return plantilla.format(n=num) if plantilla else None


def leer_textos(ruta: str) -> dict:
    """Devuelve dict {(fecha,sesion,num_votacion): row} de lo ya procesado."""
    path = Path(ruta)
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as fh:
        return {
            (r["fecha"], r["sesion"], r["num_votacion"]): r
            for r in csv.DictReader(fh)
        }


def escribir_fila(fila: dict, ruta: str, ya_existe: bool) -> None:
    path = Path(ruta)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNAS)
        if not ya_existe:
            writer.writeheader()
        writer.writerow({c: fila.get(c, "") for c in COLUMNAS})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-in", default="data/votaciones.csv")
    parser.add_argument("--out", default="data/textos.csv")
    parser.add_argument(
        "--desde", default=None, metavar="AAAAMMDD",
        help="Procesar solo sesiones con fecha >= este valor"
    )
    args = parser.parse_args()

    # Leer votaciones
    with open(args.csv_in, newline="", encoding="utf-8") as fh:
        votaciones = list(csv.DictReader(fh))

    if args.desde:
        votaciones = [r for r in votaciones if r["fecha"] >= args.desde]

    # Textos ya procesados
    ya_procesados = leer_textos(args.out)
    fichero_existe = Path(args.out).exists()

    # Agrupar por sesión para obtener URLs de una sola consulta al índice
    from collections import defaultdict
    por_sesion: dict[tuple, list] = defaultdict(list)
    for row in votaciones:
        clave = (row["fecha"], row["sesion"])
        por_sesion[clave].append(row)

    total_filas = 0
    sesiones_lista = sorted(por_sesion.keys(), key=lambda x: int(x[1]))

    for (fecha, sesion) in sesiones_lista:
        rows = por_sesion[(fecha, sesion)]
        # Saltar si todas las filas de esta sesión ya están
        claves_sesion = {(fecha, sesion, r["num_votacion"]) for r in rows}
        if claves_sesion <= set(ya_procesados.keys()):
            print(f"Sesión {sesion} ({fecha}): ya procesada, saltando.")
            continue

        print(f"Sesión {sesion} ({fecha}): {len(rows)} votaciones — obteniendo URLs...")

        # Obtener URLs del índice por fecha
        fecha_ddmmaaaa = f"{fecha[6:8]}/{fecha[4:6]}/{fecha[0:4]}"
        items_urls = sesiones_mod.obtener_sesion_por_fecha(fecha_ddmmaaaa)
        url_map = {it["num_votacion"]: it["url"] for it in items_urls}

        for row in rows:
            num = int(row["num_votacion"])
            clave = (fecha, sesion, row["num_votacion"])
            if clave in ya_procesados:
                continue

            # 1. Descargar JSON → texto_exp
            texto_exp = ""
            url = url_map.get(num)
            if url:
                try:
                    datos = _fetch_json(url)
                    info = datos.get("informacion", {})
                    texto_exp = info.get("textoExpediente", "") or ""
                    # Incluir también textoSubGrupo si hay punto
                    sub = info.get("textoSubGrupo", "") or ""
                    if sub:
                        texto_exp = texto_exp + "\n" + sub if texto_exp else sub
                except Exception as e:
                    print(f"  ERROR JSON votación {num}: {e}")
                time.sleep(PAUSA)
            else:
                print(f"  Sin URL para votación {num} (no encontrada en índice)")

            # 2. Descargar BOCG si hay expediente
            bocg_url = _bocg_url_desde_csv(row)
            if bocg_url:
                resultado = bocg.descargar_texto(bocg_url)
                texto_bocg = bocg.extraer_parte_relevante(resultado["texto"], row["tipo"])
                bocg_fuente = resultado["fuente"]
            else:
                texto_bocg = ""
                bocg_fuente = "no_disponible"

            fila = {
                "fecha":        fecha,
                "sesion":       sesion,
                "num_votacion": row["num_votacion"],
                "texto_exp":    texto_exp,
                "texto_bocg":   texto_bocg,
                "bocg_fuente":  bocg_fuente,
            }
            escribir_fila(fila, args.out, fichero_existe)
            fichero_existe = True
            ya_procesados[clave] = fila
            total_filas += 1

        print(f"  → {len(rows)} filas escritas (total: {total_filas})")

    print(f"\n✓ {total_filas} filas nuevas en {args.out}")


if __name__ == "__main__":
    main()
