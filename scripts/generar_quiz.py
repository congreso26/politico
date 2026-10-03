#!/usr/bin/env python3
"""Genera web/quiz.json desde data/votaciones.csv para la app estática del test de afinidad.

REGLAS DE ELIMINACIÓN (únicas; se aplican en este orden y el informe cuenta cada una):
  R1. Sin título o sin resumen (vacíos tras quitar espacios): se descarta. Son votaciones sin
      texto oficial publicado (correcciones técnicas, votos particulares...).
  R2. Sin voto de ningún grupo (ninguna de las 12 columnas de posición con A favor / En contra /
      Abstención / Dividido): se descarta, porque no sirve para calcular afinidad.
  R3. Repetidas: si varias votaciones tienen EXACTAMENTE el mismo título y el mismo resumen
      (p. ej. empates en que se repitió la votación del mismo punto), se conserva solo la
      ÚLTIMA en el orden del CSV (cronológico: sesión y nº de votación).
NO se elimina nada por: tipo (las enmiendas entran), resultado, grupos divididos, resumen
aproximado, confianza del texto, fecha o sesión. Las marcas (enm, tot, apr) se exportan para
que la app pueda filtrar si quiere, pero este script no las usa para quitar votaciones.

Uso: python scripts/generar_quiz.py [--out web/quiz.json]
"""
import csv, json, sys
from datetime import date
from pathlib import Path

GRUPOS = {  # clave corta -> columna del CSV
    "PP": "PP_voto", "PSOE": "PSOE_voto", "Vox": "Vox_voto", "Sumar": "Sumar_voto",
    "ERC": "ERC_voto", "Junts": "Junts_voto", "Bildu": "Bildu_voto", "PNV": "PNV_voto",
    "SumarMx": "MxSUMAR_voto", "BNG": "MxBNG_voto", "CC": "MxCCa_voto", "UPN": "MxUPN_voto",
}
CODIGO = {"A favor": "S", "En contra": "N", "Abstención": "A", "Dividido": "D"}  # "" -> omitido


def main(out: str) -> None:
    filas = list(csv.DictReader(open("data/votaciones.csv", encoding="utf-8")))
    items, r1, r2 = [], 0, 0
    for r in filas:
        if not (r["titulo"].strip() and r["resumen"].strip()):                      # R1
            r1 += 1
            continue
        f = r["fecha"]
        v = {g: CODIGO[r[c]] for g, c in GRUPOS.items() if r[c] in CODIGO}
        if not v:                                                                   # R2
            r2 += 1
            continue
        items.append({
            "id": f"{r['sesion']}-{r['num_votacion']}",
            "f": f"{f[:4]}-{f[4:6]}-{f[6:]}",
            "tipo": r["tipo"],
            "t": r["titulo"].strip(),
            "r": r["resumen"].strip(),
            "enm": r["es_enmienda"] == "True",
            "tot": r["es_enmienda_totalidad"] == "True",
            "apr": r["resumen_aproximado"] == "True",
            "res": r["resultado"],
            "sf": int(r["si_total"] or 0), "ec": int(r["no_total"] or 0), "ab": int(r["abs_total"] or 0),
            "v": v,
        })
    ultima = {(i["t"], i["r"]): k for k, i in enumerate(items)}                     # R3
    finales = [i for k, i in enumerate(items) if ultima[(i["t"], i["r"])] == k]
    r3 = len(items) - len(finales)
    meta = {"filas_csv": len(filas), "R1_sin_titulo_o_resumen": r1, "R2_sin_voto_de_ningun_grupo": r2,
            "R3_repetidas_se_conserva_la_ultima": r3}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    json.dump({"generado": date.today().isoformat(), "n": len(finales), "descartes": meta,
               "grupos": list(GRUPOS), "items": finales},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    kb = Path(out).stat().st_size / 1024
    print(f"{len(filas)} filas CSV -> {len(finales)} votaciones en {out} ({kb:.0f} KB)")
    print(f"  R1 sin título/resumen: {r1} | R2 sin voto de ningún grupo: {r2} | R3 repetidas (se queda la última): {r3}")
    print(f"  enmiendas: {sum(i['enm'] for i in finales)} | totalidad: {sum(i['tot'] for i in finales)} | aproximadas: {sum(i['apr'] for i in finales)}")


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "web/quiz.json")
