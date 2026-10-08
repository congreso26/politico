#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Guarda el título oficial literal de cada votación (textoExpediente, tituloSubGrupo, textoSubGrupo)
en data/titulos_oficiales.csv, descargando los JSON por fecha. Incremental: salta lo ya guardado.

Uso: python scripts/titulos_oficiales.py
"""
import csv
from pathlib import Path
import sesiones, votaciones

RUTA = Path("data/titulos_oficiales.csv")
COLS = ["sesion", "num_votacion", "texto_expediente", "titulo_subgrupo", "texto_subgrupo"]


def fila_titulo(datos: dict, sesion: int, num: int) -> dict:
    i = datos.get("informacion", {})
    return {"sesion": sesion, "num_votacion": num,
            "texto_expediente": (i.get("textoExpediente") or "").strip(),
            "titulo_subgrupo": (i.get("tituloSubGrupo") or "").strip(),
            "texto_subgrupo": (i.get("textoSubGrupo") or "").strip()}


def cargar() -> dict[str, dict]:
    if not RUTA.exists():
        return {}
    with open(RUTA, encoding="utf-8", newline="") as f:
        return {f"{r['sesion']}-{r['num_votacion']}": r for r in csv.DictReader(f)}


def _esperadas() -> list[tuple[str, str, str]]:
    csv.field_size_limit(10**9)
    with open("data/votaciones.csv", encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    return sorted({(r["fecha"], r["sesion"], r["num_votacion"]) for r in filas})


def _guardar(hechas: dict) -> None:
    filas = sorted(hechas.values(), key=lambda r: (int(r["sesion"]), int(r["num_votacion"])))
    with open(RUTA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(filas)


def _procesar_fecha(fecha: str, sesion: str, hechas: dict) -> int:
    dd = f"{fecha[6:]}/{fecha[4:6]}/{fecha[:4]}"
    nuevas = 0
    for it in sesiones.obtener_sesion_por_fecha(dd):
        clave = f"{it['sesion']}-{it['num_votacion']}"
        if str(it["sesion"]) != sesion or clave in hechas:
            continue
        try:
            hechas[clave] = fila_titulo(votaciones.descargar_votacion(it["url"]),
                                        it["sesion"], it["num_votacion"])
            nuevas += 1
        except Exception as e:
            print(f"  ERROR {clave}: {e}")
    return nuevas


def main() -> None:
    hechas = cargar()
    esperadas = _esperadas()
    pendientes = {(f, s) for f, s, n in esperadas if f"{s}-{n}" not in hechas}
    for fecha, ses in sorted(pendientes):
        n = _procesar_fecha(fecha, ses, hechas)
        print(fecha, ses, n, "nuevas", flush=True)
        _guardar(hechas)
    faltan = [f"{s}-{n}" for _, s, n in esperadas if f"{s}-{n}" not in hechas]
    print(f"Filas: {len(hechas)}; votaciones sin título: {len(faltan)}")
    if faltan:
        print("Faltan:", ", ".join(faltan))


if __name__ == "__main__":
    main()
