#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Genera web/textos/{sesion}-{num}.json: título oficial y texto LITERAL de lo votado.

Cada votación tiene uno o varios localizadores (documento + selector). Se toman de
data/localizadores_manual.jsonl si existen para esa votación; si no, de localizadores_auto().
El texto lo extrae siempre el código del documento oficial y se publica solo si es_literal().

Uso: python scripts/generar_textos_web.py [--solo 76-3 13-4 ...]
"""
import csv, json, re, sys, collections, functools
from pathlib import Path
import texto_oficial, titulos_oficiales
from iniciativas import FICHA

csv.field_size_limit(10**9)
OUT = Path("web/textos"); MANUAL = Path("data/localizadores_manual.jsonl")
PREFIJOS = re.compile(r"^(?:Texto resultante aprobado|Texto aprobado|Texto votado)\s*:\s*")


@functools.lru_cache(maxsize=None)
def paginas(doc: str):
    """paginas_pdf memoizado: cada PDF se parsea una vez por ejecución."""
    return texto_oficial.paginas_pdf(doc)


def localizadores_auto(f: dict) -> list[dict]:
    t, doc = f.get("texto_votado", ""), f.get("fuente_texto", "")
    vid = f"{f['sesion']}-{f['num_votacion']}"
    if t and doc and "[…]" not in t:
        return [{"id": vid, "doc": doc, "sel": {"literal": PREFIJOS.sub("", t).strip().strip("«»")}}]
    return []


def extraer(loc: dict) -> dict | None:
    pags = paginas(loc["doc"])
    if not pags:
        return None
    s = loc["sel"]
    if "literal" in s:
        t = s["literal"]
    elif "enmiendas" in s:
        partes = [texto_oficial.cortar(pags, rf"ENMIENDA NÚM\. {n}\b", r"ENMIENDA NÚM\.") for n in s["enmiendas"]]
        t = None if None in partes else "\n\n".join(partes)
    elif "desde" in s:
        t = texto_oficial.cortar(pags, s["desde"], s.get("hasta"))
    else:
        return None
    if not t or not texto_oficial.es_literal(t, pags):
        return None
    return {"texto": texto_oficial.parrafos(t), "fuente": loc["doc"], "pagina": texto_oficial.pagina_de(t, pags)}


def registro(vid: str, titulo: dict, frags: list, no_publicado: bool, exp: str) -> dict:
    sub = " · ".join(x for x in (titulo.get("titulo_subgrupo", ""), titulo.get("texto_subgrupo", "")) if x)
    estado = "literal" if frags else ("no_publicado" if no_publicado else "sin_texto")
    return {"id": vid, "titulo": titulo.get("texto_expediente", ""), "subgrupo": sub, "estado": estado,
            "fragmentos": frags, "fuente_ficha": FICHA.format(exp=exp) if re.match(r"\d{3}/\d{6}$", exp) else ""}


def manuales() -> dict[str, list[dict]]:
    out = collections.defaultdict(list)
    if MANUAL.exists():
        for ln in MANUAL.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                d = json.loads(ln); out[d["id"]].append(d)
    return out


def main(solo: set[str]) -> None:
    ids = {i["id"] for i in json.load(open("web/quiz.json", encoding="utf-8"))["items"]}
    titulos, man = titulos_oficiales.cargar(), manuales()
    OUT.mkdir(parents=True, exist_ok=True)
    informe = collections.Counter()
    for f in csv.DictReader(open("data/votaciones.csv", encoding="utf-8")):
        vid = f"{f['sesion']}-{f['num_votacion']}"
        if vid not in ids or (solo and vid not in solo):
            continue
        locs = man.get(vid) or localizadores_auto(f)
        no_pub = any(l["sel"].get("no_publicado") for l in locs)
        frags = [] if no_pub else [x for x in map(extraer, locs) if x]
        if len(frags) != len([l for l in locs if not l["sel"].get("no_publicado")]):
            frags = []  # todos o ninguno: no se publica un texto a medias
        r = registro(vid, titulos.get(vid, {}), frags, no_pub, f["expediente"])
        (OUT / f"{vid}.json").write_text(json.dumps(r, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        informe[(f["expediente"][:3], r["estado"])] += 1
    tot = collections.Counter()
    for (pre, est), n in sorted(informe.items()):
        print(f"  {pre} {est:13} {n}"); tot[est] += n
    print("TOTAL", dict(tot))
    grandes = [p.name for p in OUT.glob("*.json") if p.stat().st_size > 2_000_000]
    if grandes:
        print("AVISO ficheros > 2 MB:", grandes)


if __name__ == "__main__":
    main(set(sys.argv[sys.argv.index("--solo") + 1:]) if "--solo" in sys.argv else set())
