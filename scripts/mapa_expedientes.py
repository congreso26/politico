#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Fase 1: asigna expediente a cada votación cruzando el texto de la votación
con el orden del día de la sesión (tramit_pleno{fecha}_{N}.pdf).

Salida: data/mapa_expedientes.csv (sesion, num_votacion, expediente, score, metodo)
        tmp/mapa_validacion.csv   (filas dudosas o sin cruce)
"""
import csv, io, re, sys, time, urllib.request
from pathlib import Path
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).parent))
from orden_dia import _parsear_texto, HEADERS, BASE

CACHE = Path("data/pdf_cache")
SUFIJO = re.compile(r"\s*(?:Punto\s[\d.a-z]+|Enmiendas?\s[\d, ya]+|Voto particular[^.]*|Resto de[^.]*|Votaci[oó]n en bloque[^.]*)\.?\s*$", re.I)


def pdf_orden_dia(fecha: str, sesion: str) -> bytes | None:
    f = CACHE / f"tramit_pleno{fecha}_{sesion}.pdf"
    if f.exists():
        return f.read_bytes()
    url = f"{BASE}/tramit_pleno{fecha}_{sesion}.pdf"
    for intento in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            data = urllib.request.urlopen(req, timeout=60).read()
            CACHE.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            time.sleep(2)
    return None


def palabras(t: str) -> set[str]:
    return {w.lower() for w in re.findall(r"\b\w{5,}\b", t)}


def score(a: set, b: set) -> float:
    return len(a & b) / max(1, min(len(a), len(b)))


def main():
    vot = list(csv.DictReader(open("data/votaciones.csv", encoding="utf-8")))
    txt = {(r["sesion"], r["num_votacion"]): r for r in csv.DictReader(open("tmp/textos_antiguo.csv", encoding="utf-8"))}
    sesiones = {}
    for r in vot:
        s = sesiones.setdefault(r["sesion"], {"fecha": r["fecha"], "filas": []})
        s["fecha"] = min(s["fecha"], r["fecha"])
        s["filas"].append(r)
    out, dudosas = [], []
    for ses in sorted(sesiones, key=int):
        info = sesiones[ses]
        data = pdf_orden_dia(info["fecha"], ses)
        items = []
        if data:
            try:
                texto = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)
                items = _parsear_texto(texto)
            except Exception:
                pass
        pal_items = [palabras(it["texto"]) for it in items]
        for r in info["filas"]:
            k = (ses, r["num_votacion"])
            t = SUFIJO.sub("", (txt.get(k, {}).get("texto_exp") or "").strip())
            pv = palabras(t)
            best, bs = None, 0.0
            for it, pi in zip(items, pal_items):
                sc = score(pv, pi) if pv and pi else 0.0
                if sc > bs:
                    best, bs = it, sc
            exp = best["expediente"] if best and bs >= 0.5 else ""
            out.append({"sesion": ses, "num_votacion": r["num_votacion"], "expediente": exp,
                        "score": f"{bs:.2f}", "metodo": "orden_dia" if exp else "",
                        "bocg_serie": best["bocg_serie"] if exp else "", "bocg_num": best["bocg_num"] if exp else "",
                        "n_items": len(items), "texto": t[:120]})
        print(ses, info["fecha"], "items", len(items), "filas", len(info["filas"]), flush=True)
    with open("data/mapa_expedientes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print("con expediente", sum(1 for o in out if o["expediente"]), "de", len(out))


if __name__ == "__main__":
    main()
