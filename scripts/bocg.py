#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Descarga PDFs del BOCG y extrae el texto relevante de cada iniciativa.
"""

import io
import urllib.request
from pypdf import PdfReader

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; scraper-congreso/1.0)"}


def descargar_texto(bocg_url: str | None) -> dict:
    """
    Descarga el PDF del BOCG y extrae el texto.

    Devuelve:
      {
        "texto":  str,   # texto extraído, puede ser ""
        "fuente": "bocg" | "no_disponible" | "error_404" | "error_otro",
        "url":    bocg_url
      }
    """
    if bocg_url is None:
        return {"texto": "", "fuente": "no_disponible", "url": None}

    try:
        req = urllib.request.Request(bocg_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        reader = PdfReader(io.BytesIO(data))
        texto = "\n".join(p.extract_text() or "" for p in reader.pages)
        return {"texto": texto, "fuente": "bocg", "url": bocg_url}

    except urllib.error.HTTPError as e:
        fuente = "error_404" if e.code == 404 else "error_otro"
        return {"texto": "", "fuente": fuente, "url": bocg_url}
    except Exception:
        return {"texto": "", "fuente": "error_otro", "url": bocg_url}


def extraer_parte_relevante(texto_completo: str, tipo: str) -> str:
    """
    Para tipo="PNL": devuelve el bloque desde "El Congreso de los Diputados insta"
      hasta "Palacio del Congreso" o fin. Si no lo encuentra, devuelve los últimos 2000 chars.
    Para otros tipos: texto truncado a 4000 chars.
    """
    if not texto_completo:
        return ""

    if tipo == "PNL":
        import re
        m = re.search(
            r"(El Congreso de los Diputados insta.+?)(?=Palacio del Congreso|$)",
            texto_completo,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            return m.group(1).strip()
        return texto_completo[-2000:].strip()

    return texto_completo[:4000].strip()


if __name__ == "__main__":
    tests = [
        ("BOCG-15-D-519 (debería existir)",
         "https://www.congreso.es/public_oficiales/L15/CONG/BOCG/D/BOCG-15-D-519.PDF"),
        ("BOCG-15-D-518 (probable 404)",
         "https://www.congreso.es/public_oficiales/L15/CONG/BOCG/D/BOCG-15-D-518.PDF"),
    ]
    for desc, url in tests:
        print(f"\n--- {desc} ---")
        resultado = descargar_texto(url)
        print(f"Fuente: {resultado['fuente']}")
        if resultado["texto"]:
            print(f"Texto (primeros 300 chars):\n{resultado['texto'][:300]}")
            relevante = extraer_parte_relevante(resultado["texto"], "PNL")
            print(f"\nParte relevante (PNL, primeros 300 chars):\n{relevante[:300]}")
