#!/usr/bin/env python3
"""
Obtiene los enlaces a las votaciones JSON de la página de opendata del Congreso.

Funciones públicas
------------------
obtener_sesion_actual() -> list[dict]
    Scrapea el índice de opendata y extrae todos los links JSON de votación
    de la sesión más reciente publicada.

desde_urls(urls) -> list[dict]
    Construye la misma estructura a partir de una lista de URLs dada
    manualmente (útil para sesiones históricas o tests).

Cada dict tiene estas claves:
    sesion        int   número de sesión (p. ej. 202)
    fecha         str   "AAAAMMDD" (p. ej. "20260930")
    num_votacion  int   número de votación dentro de la sesión (p. ej. 1)
    url           str   URL absoluta al fichero JSON
"""

import re
import urllib.request

BASE_URL = "https://www.congreso.es"
OPENDATA_URL = f"{BASE_URL}/es/opendata/votaciones"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; scraper-congreso/1.0)"}

# Patrón que coincide con los paths de votación individuales:
#   /webpublica/opendata/votaciones/Leg15/Sesion202/20260930/Votacion001/VOT_....json
_PATH_RE = re.compile(
    r"/webpublica/opendata/votaciones/Leg\d+/Sesion(\d+)/(\d{8})/Votacion(\d+)/[^\"']+\.json",
    re.IGNORECASE,
)


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
        ct = resp.headers.get_content_charset() or "utf-8"
    return raw.decode(ct, errors="replace")


def _path_to_dict(path: str) -> dict | None:
    m = _PATH_RE.search(path)
    if not m:
        return None
    return {
        "sesion": int(m.group(1)),
        "fecha": m.group(2),
        "num_votacion": int(m.group(3)),
        "url": BASE_URL + path if path.startswith("/") else path,
    }


def obtener_sesion_actual() -> list[dict]:
    """
    Scrapea el índice de opendata y extrae todos los links JSON de votación.
    Devuelve lista de dicts ordenada por num_votacion:
      {"sesion": 202, "fecha": "20260930", "num_votacion": 1, "url": "https://...json"}
    """
    html = _fetch(OPENDATA_URL)
    resultados = []
    seen = set()
    for m in _PATH_RE.finditer(html):
        path = m.group(0)
        if path in seen:
            continue
        seen.add(path)
        entry = _path_to_dict(path)
        if entry:
            resultados.append(entry)
    resultados.sort(key=lambda d: d["num_votacion"])
    return resultados


def desde_urls(urls: list[str]) -> list[dict]:
    """
    Construye la misma estructura desde una lista de URLs pasadas manualmente.
    Lanza ValueError si alguna URL no encaja con el patrón esperado.
    """
    resultados = []
    for url in urls:
        path = url.replace(BASE_URL, "")
        entry = _path_to_dict(path)
        if entry is None:
            raise ValueError(f"URL no reconocida: {url!r}")
        entry["url"] = url if url.startswith("http") else BASE_URL + url
        resultados.append(entry)
    resultados.sort(key=lambda d: d["num_votacion"])
    return resultados


if __name__ == "__main__":
    print(f"Consultando {OPENDATA_URL} ...")
    votaciones = obtener_sesion_actual()
    if not votaciones:
        print("No se encontraron votaciones.")
    else:
        sesion = votaciones[0]["sesion"]
        fecha = votaciones[0]["fecha"]
        print(f"\nSesión {sesion} — {fecha} — {len(votaciones)} votaciones:\n")
        for v in votaciones:
            print(f"  Votacion {v['num_votacion']:03d}  {v['url']}")
