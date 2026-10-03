#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Fase 2: dado un expediente (p. ej. 162/000117), localiza su texto en el BOCG
y escribe data/iniciativas/{tipo}_{num}.json.

Uso:  python scripts/iniciativas.py 162/000117 [173/000003 ...]
"""
import io, json, re, sys, time, urllib.request, urllib.error
from pathlib import Path
from pypdf import PdfReader

H = {"User-Agent": "Mozilla/5.0"}
CACHE = Path("data/pdf_cache"); OUT = Path("data/iniciativas")
FICHA = ("https://www.congreso.es/es/busqueda-de-iniciativas?p_p_id=iniciativas&p_p_lifecycle=0"
         "&p_p_state=normal&p_p_mode=view&_iniciativas_mode=mostrarDetalle"
         "&_iniciativas_legislatura=XV&_iniciativas_id={exp}")
BASE = "https://www.congreso.es"


def get(url: str, cache_name: str | None = None) -> bytes | None:
    f = CACHE / cache_name if cache_name else None
    if f and f.exists():
        return f.read_bytes()
    for _ in range(3):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=60).read()
            if f:
                CACHE.mkdir(parents=True, exist_ok=True); f.write_bytes(data)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2)
        except Exception:
            time.sleep(2)
    return None


def enlaces_ficha(exp: str) -> list[dict]:
    """Enlaces a BOCG/Diario de Sesiones que cita la ficha de la iniciativa."""
    h = get(FICHA.format(exp=exp))
    if not h:
        return []
    h = h.decode("utf-8", "ignore")
    out, vistos = [], set()
    for m in re.finditer(r'href="(/public_oficiales/[^"#]+\.PDF)(?:#page=(\d+))?"', h):
        u = BASE + m.group(1)
        k = (u, m.group(2))
        if k in vistos:
            continue
        vistos.add(k)
        out.append({"url": u, "page": int(m.group(2)) if m.group(2) else None})
    return out


def texto_pdf(url: str) -> str | None:
    data = get(url, url.rsplit("/", 1)[1])
    if not data:
        return None
    try:
        r = PdfReader(io.BytesIO(data))
        t = "\n".join(p.extract_text() or "" for p in r.pages)
    except Exception:
        return None
    t = re.sub(r"cve: BOCG[^\n]*\n|BOLETÍN OFICIAL DE LAS CORTES GENERALES\n|CONGRESO DE LOS DIPUTADOS\nSerie [^\n]*\n", "", t)
    return t


def bloque(texto: str, exp: str) -> str:
    """Texto de la iniciativa: desde la última aparición de `exp` como cabecera hasta la siguiente."""
    pos = [m.start() for m in re.finditer(r"(?m)^" + re.escape(exp) + r"\s*$", texto)]
    if not pos:
        return ""
    ini = pos[-1] if len(pos) > 1 else pos[0]
    # varias apariciones: el cuerpo es la que tiene más texto hasta la siguiente cabecera
    mejor = ""
    for p in pos:
        sig = re.search(r"(?m)^\d{3}/\d{6}(?: y \d{3}/\d{6})?\s*$", texto[p + 12:])
        b = texto[p: p + 12 + sig.start()] if sig else texto[p:]
        if len(b) > len(mejor):
            mejor = b
    return mejor


def puntos(b: str) -> dict:
    """Parte el bloque dispositivo ('insta al Gobierno a: ...') en puntos numerados.
    Soporta marcadores 1. / 1.º / 1) / a) / guiones largos / 'Primero.'; si no hay lista, un único punto."""
    ms = list(re.finditer(r"(?:insta|instar|acuerda)\b[^:]{0,300}:", b))
    if not ms:
        return {}
    s = b[ms[-1].end():]
    s = re.split(r"\n\s*(?:Palacio del Congreso|http://www\.congreso|Enmienda\s*\n|Justificación)", s)[0]
    s = s.strip().strip("«»").strip()
    patrones = [
        r"(?m)^\s*(\d{1,2})\s*[.º°)]+\s*[ºª]?\s*",
        r"(?m)^\s*(?:\()?([a-z])\)\s+",
        r"(?m)^\s*()[—–]\s+",
        r"(?m)^\s*(Primer[oa]|Segund[oa]|Tercer[oa]|Cuart[oa]|Quint[oa]|Sext[oa]|Séptim[oa]|Octav[oa]|Noven[oa]|Décim[oa])[.:]\s*",
    ]
    for pat in patrones:
        partes = re.split(pat, s)
        if len(partes) >= 5:  # al menos 2 marcadores
            out = {}
            for i in range(1, len(partes) - 1, 2):
                txt = re.sub(r"\s+", " ", partes[i + 1]).strip(" »«")
                out[str(len(out) + 1)] = txt
            return out
    return {"1": re.sub(r"\s+", " ", s).strip(" »«")} if s else {}


def procesar(exp: str) -> dict:
    res = {"expediente": exp, "tipo": exp.split("/")[0], "fuentes": [], "texto_puntos": {},
           "texto_completo": "", "estado": "sin_texto", "notas": ""}
    cand = enlaces_ficha(exp)
    for c in cand:
        if "/BOCG/" not in c["url"]:
            continue
        t = texto_pdf(c["url"])
        if not t:
            res["notas"] += f"fallo {c['url']}; "
            continue
        b = bloque(t, exp)
        if len(b) > 300:
            res["fuentes"].append(c["url"])
            res["texto_completo"] = b
            res["texto_puntos"] = puntos(b)
            res["estado"] = "ok" if res["texto_puntos"] or res["tipo"] not in ("162", "173") else "revisar"
            break
    if not cand:
        res["notas"] += "ficha sin enlaces; "
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (exp.replace("/", "_") + ".json")).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


if __name__ == "__main__":
    for e in sys.argv[1:]:
        r = procesar(e)
        print(e, r["estado"], r["fuentes"], len(r["texto_puntos"]), "puntos", r["notas"])
