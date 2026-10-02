#!/usr/bin/env python3
"""
Agregación de votos por grupo parlamentario.

Dado el campo 'votaciones' de un JSON de votación, calcula la posición
de cada grupo (A favor / En contra / Abstención / Dividido),
desglosando el Grupo Mixto por partido usando mixto_partidos.json.
"""

import json
import collections
import urllib.request
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; scraper-congreso/1.0)"}

# Códigos de grupo → nombre corto
CODIGOS = {
    "GP": "PP",
    "GS": "PSOE",
    "GVOX": "Vox",
    "GSUMAR": "Sumar",
    "GR": "ERC",
    "GJxCAT": "Junts",
    "GEH Bildu": "Bildu",
    "GV (EAJ-PNV)": "PNV",
    # GMx se trata aparte
}

OPCIONES = ("Sí", "No", "Abstención")
LABELS = {"Sí": "A favor", "No": "En contra", "Abstención": "Abstención"}


def _cargar_mixto(ruta: str) -> dict:
    path = Path(ruta)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _posicion_grupo(contador: collections.Counter) -> str:
    total = sum(contador.values())
    if total == 0:
        return "Dividido"
    for opcion in OPCIONES:
        if contador[opcion] > total / 2:
            return LABELS[opcion]
    return "Dividido"


def agregar(votaciones: list[dict], ruta_mixto: str = "data/mixto_partidos.json") -> dict:
    """
    Dado el campo 'votaciones' de un JSON, devuelve posición de cada grupo:
      {"PP": "A favor", "PSOE": "En contra", "MxBNG": "A favor", ...}

    Solo incluye grupos con al menos 1 voto registrado.
    Prefijo "Mx" para partidos desglosados del Grupo Mixto.
    """
    mixto_map = _cargar_mixto(ruta_mixto)
    grupos: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)

    for entrada in votaciones:
        codigo   = entrada.get("grupo", "")
        voto     = entrada.get("voto", "No vota")
        diputado = entrada.get("diputado", "")

        if codigo == "GMx":
            formacion = mixto_map.get(diputado)
            nombre_grupo = ("Mx" + formacion) if formacion else "MxOtro"
        else:
            nombre_grupo = CODIGOS.get(codigo, codigo)

        grupos[nombre_grupo][voto] += 1

    return {nombre: _posicion_grupo(c) for nombre, c in grupos.items()}


if __name__ == "__main__":
    URL = (
        "https://www.congreso.es/webpublica/opendata/votaciones/"
        "Leg15/Sesion202/20260930/Votacion001/VOT_20260930153547.json"
    )
    print(f"Descargando votación de prueba...\n  {URL}\n")
    req = urllib.request.Request(URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        datos = json.loads(resp.read().decode("utf-8"))

    info    = datos.get("informacion", {})
    totales = datos.get("totales", {})
    print(
        f"Sesión {info.get('sesion')} · Votación {info.get('numeroVotacion')} "
        f"({info.get('fecha')})"
    )
    print(f"Expediente: {info.get('textoExpediente', '')[:80].strip()}")
    print(
        f"Totales: {totales.get('afavor')} sí / "
        f"{totales.get('enContra')} no / "
        f"{totales.get('abstenciones')} abst.\n"
    )

    posiciones = agregar(datos["votaciones"])

    por_posicion: dict[str, list[str]] = collections.defaultdict(list)
    for grupo, pos in sorted(posiciones.items()):
        por_posicion[pos].append(grupo)

    for pos in ("A favor", "En contra", "Abstención", "Dividido"):
        grupos_pos = por_posicion.get(pos, [])
        if grupos_pos:
            print(f"  {pos:12s}: {', '.join(grupos_pos)}")
