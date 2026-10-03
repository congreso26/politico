#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Vuelca data/resumenes/*.jsonl (titulo, resumen, aproximado) en data/votaciones.csv.
No toca filas que ya tengan título (p. ej. sesión 202)."""
import csv, glob, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from csv_io import COLUMNAS

res = {}
for f in sorted(glob.glob("data/resumenes/*.jsonl")):
    for l in open(f, encoding="utf-8"):
        d = json.loads(l); res[(d["sesion"], d["num_votacion"])] = d
rows = list(csv.DictReader(open("data/votaciones.csv", encoding="utf-8")))
n = 0
for r in rows:
    d = res.get((r["sesion"], r["num_votacion"]))
    if d and not r.get("titulo"):
        r["titulo"], r["resumen"] = d["titulo"], d["resumen"]
        r["resumen_aproximado"] = "True" if d.get("aproximado") else ""
        r["sin_texto"] = "True" if not r.get("texto_votado") else ""
        n += 1
with open("data/votaciones.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=COLUMNAS); w.writeheader()
    for r in rows: w.writerow({c: r.get(c, "") for c in COLUMNAS})
print("volcadas", n, "| con título:", sum(1 for r in rows if r.get("titulo")), "de", len(rows))
