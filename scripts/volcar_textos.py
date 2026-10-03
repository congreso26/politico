#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Vuelca data/votaciones_texto/*.jsonl en data/votaciones.csv (texto_votado, confianza_texto,
fuente_texto) y corrige `expediente` cuando el agente lo corrigió."""
import csv, glob, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from csv_io import COLUMNAS

textos = {}
for f in sorted(glob.glob("data/votaciones_texto/*.jsonl")):
    for l in open(f, encoding="utf-8"):
        d = json.loads(l)
        textos[(d["sesion"], d["num_votacion"])] = d
rows = list(csv.DictReader(open("data/votaciones.csv", encoding="utf-8")))
cambios = []
for r in rows:
    d = textos.get((r["sesion"], r["num_votacion"]))
    if not d:
        continue
    e = d.get("expediente") or ""
    if e and e != r.get("expediente"):
        cambios.append((r["sesion"], r["num_votacion"], r.get("expediente", ""), e))
        r["expediente"] = e
    r["texto_votado"] = d.get("texto_votado", "")
    r["confianza_texto"] = d.get("confianza", "")
    r["fuente_texto"] = d.get("fuente_url", "")
with open("data/votaciones.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=COLUMNAS); w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in COLUMNAS})
print("votaciones con texto:", sum(1 for r in rows if r.get("texto_votado")), "de", len(rows))
print("expedientes corregidos/añadidos:", len(cambios))
Path("tmp/expedientes_corregidos.csv").write_text("sesion,num,antes,despues\n" + "\n".join(",".join(c) for c in cambios), encoding="utf-8")
