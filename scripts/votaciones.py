#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Descarga JSONs de votaciones individuales del Congreso de los Diputados.
"""

import json
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; scraper-congreso/1.0)"}


def descargar_votacion(url: str) -> dict:
    """
    Descarga el JSON de una votación y lo devuelve parseado.
    Lanza excepción si falla la descarga o el JSON está malformado.
    """
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def descargar_todas(items: list[dict]) -> list[dict]:
    """
    items = output de sesiones.obtener_sesion_actual()
    Cada item: {"sesion": 202, "fecha": "20260930", "num_votacion": 1, "url": "..."}
    Devuelve misma lista con "datos": el JSON descargado añadido a cada dict.
    """
    resultado = []
    for item in items:
        print(f"  Descargando votación {item['num_votacion']:03d}...", end=" ", flush=True)
        datos = descargar_votacion(item["url"])
        print("ok")
        resultado.append({**item, "datos": datos})
    return resultado


if __name__ == "__main__":
    URL_TEST = (
        "https://www.congreso.es/webpublica/opendata/votaciones/"
        "Leg15/Sesion202/20260930/Votacion001/VOT_20260930153547.json"
    )
    print(f"Descargando votación de prueba...\n  {URL_TEST}\n")
    datos = descargar_votacion(URL_TEST)
    print("=== informacion ===")
    print(json.dumps(datos["informacion"], ensure_ascii=False, indent=2))
    print("\n=== totales ===")
    print(json.dumps(datos["totales"], ensure_ascii=False, indent=2))
