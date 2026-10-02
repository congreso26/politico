#!/usr/bin/env python3
"""
Descarga el CSV de diputados activos del Congreso (XV Legislatura),
filtra los del Grupo Mixto y genera mixto_partidos.json con el mapeo:

    {"Apellidos, Nombre": "FormacionElectoral", ...}

El campo FORMACIONELECTORAL del CSV es el partido con el que concurrió
a las elecciones (PP, Podemos, BNG, CC, UPN, Compromís…), que es lo que
queremos para desglosar el Mixto.

Uso:
    python scripts/descargar_mixto.py
    python scripts/descargar_mixto.py --out data/mixto_partidos.json
"""

import csv
import io
import json
import argparse
import urllib.request
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; scraper-congreso/1.0)"}

# URL del CSV de diputados activos (se puede actualizar si cambia el timestamp)
CSV_URL = (
    "https://www.congreso.es/webpublica/opendata/diputados/"
    "DiputadosActivos__20261002050007.csv"
)

# Cadena que identifica el Grupo Mixto en el CSV
MIXTO_MARKER = "Mixto"


def fetch_csv(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
        # El CSV viene con BOM UTF-8
        return raw.decode("utf-8-sig")


def parse_mixto(csv_text: str) -> dict:
    """
    Devuelve {nombre: formacion_electoral} para todos los diputados
    cuyo GRUPOPARLAMENTARIO contiene 'Mixto' y sin fecha de baja
    (FECHABAJAENGRUPOPARLAMENTARIO vacía → sigue activo en el grupo).
    """
    reader = csv.DictReader(io.StringIO(csv_text), delimiter=";")
    mapping = {}
    for row in reader:
        grupo = row.get("GRUPOPARLAMENTARIO", "")
        baja = row.get("FECHABAJAENGRUPOPARLAMENTARIO", "").strip()
        if MIXTO_MARKER not in grupo:
            continue
        if baja:
            continue  # ya no está en el grupo
        nombre = row.get("NOMBRE", "").strip()
        formacion = row.get("FORMACIONELECTORAL", "").strip() or "Mixto"
        if nombre:
            mapping[nombre] = formacion
    return mapping


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/mixto_partidos.json")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Descargando CSV de diputados activos...\n  {CSV_URL}")
    csv_text = fetch_csv(CSV_URL)
    print(f"  {len(csv_text)} caracteres descargados.")

    mapping = parse_mixto(csv_text)

    if not mapping:
        print("No se encontraron diputados del Grupo Mixto.")
        return

    print(f"\nDiputados del Grupo Mixto ({len(mapping)}):")
    for nombre, partido in sorted(mapping.items()):
        print(f"  {nombre:45s}  {partido}")

    out_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGuardado: {out_path}")


if __name__ == "__main__":
    main()
