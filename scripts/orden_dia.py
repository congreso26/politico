#!/usr/bin/env python3
"""
Descarga y parsea el PDF del orden del día del Pleno del Congreso.

URL patrón: https://www.congreso.es/docu/tramit/LegXV/tramit_pleno{AAAAMMDD}_{N}.pdf

Devuelve una lista de items con expediente, BOCG y descripción textual,
que permite cruzar los JSONs de votación con sus expedientes reales.
"""

import io
import re
import urllib.request
from pypdf import PdfReader

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; scraper-congreso/1.0)"}

BASE = "https://www.congreso.es/docu/tramit/LegXV"

# Regex para extraer expedientes del PDF
_RE_EXPTE   = re.compile(r"N[uú]m\.\s*expte\.\s*([\d]+/[\d]+)", re.IGNORECASE)
_RE_BOCG_CG = re.compile(
    r'"BOCG\.\s*Cortes Generales"[^,]*,\s*serie\s*([A-Z])[^,]*,\s*n[uú]m(?:ero)?\.?\s*(\d+)',
    re.IGNORECASE,
)
_RE_BOCG_CD = re.compile(
    r'"BOCG\.\s*Congreso de los Diputados"[^,]*,\s*serie\s*([A-Z])[^,]*,\s*n[uú]m(?:ero)?\.?\s*(\d+)',
    re.IGNORECASE,
)


def _bocg_url(serie: str, num: str, tipo_expte: str) -> str | None:
    """Construye la URL del BOCG a partir de serie y número."""
    n = str(int(num))  # elimina ceros iniciales
    s = serie.upper()
    if tipo_expte.startswith("110"):  # convenio → BOCG Cortes Generales
        return f"https://www.congreso.es/public_oficiales/L15/CORT/BOCG/A/BOCG-15-CG-A-{n}.PDF"
    elif s == "D":
        return f"https://www.congreso.es/public_oficiales/L15/CONG/BOCG/D/BOCG-15-D-{n}.PDF"
    elif s == "A":
        return f"https://www.congreso.es/public_oficiales/L15/CONG/BOCG/A/BOCG-15-A-{n}-1.PDF"
    elif s == "B":
        return f"https://www.congreso.es/public_oficiales/L15/CONG/BOCG/B/BOCG-15-B-{n}-1.PDF"
    return None


def descargar_orden_dia(fecha: str, sesion: int) -> list[dict]:
    """
    Descarga el PDF del orden del día y devuelve lista de items:
    [
      {
        "expediente": "162/000814",
        "tipo_prefix": "162",
        "bocg_url": "https://...",
        "bocg_serie": "D",
        "bocg_num": "569",
        "texto": "Del Grupo Parlamentario Popular...",
      },
      ...
    ]
    Devuelve [] si el PDF no está disponible.
    """
    url = f"{BASE}/tramit_pleno{fecha}_{sesion}.pdf"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    except Exception:
        return []

    try:
        reader = PdfReader(io.BytesIO(data))
        texto_total = "\n".join(p.extract_text() or "" for p in reader.pages)
    except Exception:
        return []

    return _parsear_texto(texto_total)


def _parsear_texto(texto: str) -> list[dict]:
    """
    Parsea el texto completo del PDF y extrae todos los items con expediente.

    Estrategia: encuentra todas las posiciones de "(Núm. expte. XXX/XXXXXX)"
    y para cada una, el bloque descriptivo es el texto entre la posición
    del expediente ANTERIOR y la del actual. Así evitamos capturar texto
    de otros items.
    """
    # Encontrar todos los matches de expediente con sus posiciones
    matches = list(_RE_EXPTE.finditer(texto))
    if not matches:
        return []

    items = []
    for i, m_expte in enumerate(matches):
        expte = m_expte.group(1)
        tipo_prefix = expte.split("/")[0]

        # Bloque: desde el fin del expediente anterior (o inicio del texto)
        # hasta el inicio del expediente actual
        inicio_bloque = matches[i - 1].end() if i > 0 else 0
        bloque = texto[inicio_bloque:m_expte.start()]

        # Limpiar encabezados de página y columnas de tabla
        bloque = re.sub(r"ASUNTO DISCUTIDO[^\n]*", "", bloque)
        bloque = re.sub(r"APROBADO[^\n]*", "", bloque)
        bloque = re.sub(r"ENV[IÍ]OS[^\n]*", "", bloque)
        bloque = re.sub(r"COMUNICACIONES[^\n]*", "", bloque)
        bloque = bloque.strip()

        # Extraer la referencia BOCG más cercana al expediente (la última del bloque)
        bocg_url = None
        bocg_serie = ""
        bocg_num = ""

        for regex in (_RE_BOCG_CG, _RE_BOCG_CD):
            todos = regex.findall(bloque)
            if todos:
                bocg_serie, bocg_num = todos[-1]  # la última = más cercana
                bocg_serie = bocg_serie.upper()
                bocg_url = _bocg_url(bocg_serie, bocg_num, expte)
                break

        # Texto descriptivo: quitar la parte del BOCG (todo desde la última cita)
        texto_item = re.sub(r'"BOCG\..*', "", bloque, flags=re.DOTALL).strip()
        texto_item = re.sub(r"\s+", " ", texto_item).strip()

        items.append({
            "expediente":  expte,
            "tipo_prefix": tipo_prefix,
            "bocg_url":    bocg_url,
            "bocg_serie":  bocg_serie,
            "bocg_num":    bocg_num,
            "texto":       texto_item,
        })

    return items


def buscar_expediente(texto_votacion: str, items: list[dict]) -> dict | None:
    """
    Dado el textoExpediente de un JSON de votación y la lista de items del orden del día,
    devuelve el item más probable por superposición de texto.

    Estrategia: normaliza ambos textos y busca el item cuya descripción tenga mayor
    superposición de palabras clave con el texto de la votación.
    """
    if not items or not texto_votacion:
        return None

    def palabras_clave(t: str) -> set[str]:
        # Palabras de más de 5 chars, en minúsculas
        return {w.lower() for w in re.findall(r"\b\w{5,}\b", t)}

    palabras_vot = palabras_clave(texto_votacion)
    if not palabras_vot:
        return None

    mejor = None
    mejor_score = 0
    for item in items:
        palabras_item = palabras_clave(item["texto"])
        if not palabras_item:
            continue
        comunes = palabras_vot & palabras_item
        score = len(comunes) / max(len(palabras_vot), len(palabras_item))
        if score > mejor_score:
            mejor_score = score
            mejor = item

    # Umbral mínimo de similitud
    return mejor if mejor_score >= 0.3 else None


if __name__ == "__main__":
    items = descargar_orden_dia("20260930", 202)
    print(f"Items extraídos del orden del día: {len(items)}\n")
    for it in items:
        print(f"  {it['expediente']:15s}  BOCG={it['bocg_num'] or '-':5s}  {it['texto'][:80]}")
