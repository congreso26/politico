#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Extracción LITERAL de texto de documentos oficiales (BOCG/BOE) y su verificación.

Transformaciones permitidas (únicas): quitar cabecera/pie del BOCG y U+200B, unir líneas de un
mismo párrafo. es_literal() comprueba que un fragmento está tal cual (salvo espacios y signos)
en el documento: nada que no lo pase se publica en la web.
"""
import io, re, unicodedata
from pathlib import Path
from pypdf import PdfReader
import iniciativas

CABECERA = re.compile(r"(?m)^(?:cve: BOCG[^\n]*|BOLETÍN OFICIAL DE LAS CORTES GENERALES|CONGRESO DE LOS DIPUTADOS"
                      r"|CORTES GENERALES|Serie [A-Z]+ Núm\.[^\n]*Pág\. \d+)\s*\n?")


def limpiar(t: str) -> str:
    return CABECERA.sub("", t.replace("\u200b", "")).strip()


def paginas_pdf(ruta_o_url: str) -> list[str] | None:
    if ruta_o_url.startswith("http"):
        data = iniciativas.get(ruta_o_url, ruta_o_url.split("#")[0].rsplit("/", 1)[1])
    else:
        p = Path(ruta_o_url); data = p.read_bytes() if p.exists() else None
    if not data:
        return None
    try:
        return [limpiar(pg.extract_text() or "") for pg in PdfReader(io.BytesIO(data)).pages]
    except Exception:
        return None


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).replace("\u200b", "").lower()
    return re.sub(r"[\W_]+", "", s)


def es_literal(fragmento: str, paginas: list[str]) -> bool:
    f = norm(fragmento)
    return len(f) >= 20 and f in norm("\n".join(paginas))


def pagina_de(fragmento: str, paginas: list[str]) -> int | None:
    cab = norm(fragmento)[:120]
    acum = ""
    for i, p in enumerate(paginas, 1):
        acum += norm(p)
        if cab in acum:
            return i
    return None


MARCADOR = re.compile(r"^(?:\d{1,2}\s*[.º)]|[a-z]\)|[—–-]\s|Artículo|ENMIENDA NÚM\.|Disposición|Primer|Segund|Tercer)")


def parrafos(s: str) -> str:
    out = []
    for ln in (l.strip() for l in s.splitlines()):
        if not ln:
            continue
        if out and not out[-1].endswith((".", ":", ";")) and not MARCADOR.match(ln):
            out[-1] += " " + ln
        else:
            out.append(ln)
    return "\n\n".join(out)


def cortar(paginas: list[str], desde: str, hasta: str | None) -> str | None:
    doc = "\n".join(paginas)
    m = re.search(desde, doc)
    if not m:
        return None
    fin = re.search(hasta, doc[m.end():]) if hasta else None
    return doc[m.start(): m.end() + fin.start() if fin else len(doc)].strip()
