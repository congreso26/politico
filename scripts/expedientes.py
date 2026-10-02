#!/usr/bin/env python3
"""
Clasificación de expedientes parlamentarios.

Dado el campo 'informacion' de un JSON de votación del Congreso, devuelve
metadatos estructurados: tipo de iniciativa, expediente, grupo proponente,
URL del BOCG, etc.
"""

import re

# Prefijos de expediente → tipo
_PREFIJOS = {
    "162/": "PNL",
    "173/": "mocion",
    "121/": "proyecto_ley",
    "122/": "proposicion_ley",
    "110/": "convenio",
}

# Fragmentos del nombre largo → etiqueta corta
_GRUPOS = [
    ("Popular",     "PP"),
    ("Socialista",  "PSOE"),
    ("VOX",         "Vox"),
    ("Sumar",       "Sumar"),
    ("Republicano", "ERC"),
    ("Junts",       "Junts"),
    ("Bildu",       "Bildu"),
    ("Vasco",       "PNV"),
    ("Mixto",       "Mixto"),
]

# Plantillas de URL BOCG por tipo
_BOCG_URL = {
    "PNL":             "https://www.congreso.es/public_oficiales/L15/CONG/BOCG/D/BOCG-15-D-{num}.PDF",
    "proyecto_ley":    "https://www.congreso.es/public_oficiales/L15/CONG/BOCG/A/BOCG-15-A-{num}-1.PDF",
    "proposicion_ley": "https://www.congreso.es/public_oficiales/L15/CONG/BOCG/B/BOCG-15-B-{num}-1.PDF",
    "convenio":        "https://www.congreso.es/public_oficiales/L15/CORT/BOCG/A/BOCG-15-CG-A-{num}.PDF",
    "mocion":          None,
    "otro":            None,
}

_RE_GRUPO = re.compile(r"del Grupo Parlamentario ([^,\n]+)")
_RE_EXPEDIENTE = re.compile(r"\b(\d{3}/\d+)\b")
_RE_PUNTO = re.compile(r"(Punto\s+\d+)", re.IGNORECASE)


def _tipo_desde_texto(texto_exp: str, titulo: str) -> str:
    """Detecta el tipo de iniciativa a partir del texto descriptivo."""
    t = (texto_exp + " " + titulo).lower()
    if re.search(r"moción consecuencia|mocion consecuencia", t):
        return "mocion"
    if re.search(r"proyecto de ley", t):
        return "proyecto_ley"
    if re.search(r"proposición de ley|proposicion de ley", t) and "no de ley" not in t:
        return "proposicion_ley"
    # Convenio: incluye acuerdos y protocolos internacionales
    if re.search(r"convenio|acuerdo.*reino|protocolo adicional|acuerdo sobre", t):
        return "convenio"
    if re.search(r"proposición no de ley|proposicion no de ley", t):
        return "PNL"
    # Fallback por título genérico de sección
    if re.search(r"proposiciones no de ley", titulo, re.IGNORECASE):
        return "PNL"
    if re.search(r"mociones", titulo, re.IGNORECASE):
        return "mocion"
    if re.search(r"convenios internacionales", titulo, re.IGNORECASE):
        return "convenio"
    return "otro"


def clasificar(informacion: dict, orden_dia_item: dict | None = None) -> dict:
    """
    Dado el campo 'informacion' de un JSON de votación, devuelve:
    {
      "tipo":                  "PNL"|"mocion"|"proyecto_ley"|"proposicion_ley"|"convenio"|"otro",
      "expediente":            "162/000814" | None,
      "num_bocg":              "814" | None,
      "punto":                 "Punto 2" | None,
      "grupo_inicia":          "PP"|"Gobierno"|...|None,
      "bocg_url":              "https://..." | None,
      "es_enmienda_totalidad": bool,
    }

    Si se proporciona orden_dia_item (de orden_dia.buscar_expediente()),
    usa su expediente y bocg_url directamente (más fiable que parsear el texto).
    """
    texto_exp = informacion.get("textoExpediente", "") or ""
    texto_sub = informacion.get("textoSubGrupo", "") or ""
    titulo    = informacion.get("titulo", "") or ""

    # 1. Expediente y tipo
    if orden_dia_item:
        expediente   = orden_dia_item["expediente"]
        bocg_url     = orden_dia_item["bocg_url"]
        tipo_prefix  = orden_dia_item["tipo_prefix"]
        tipo         = _PREFIJOS.get(tipo_prefix + "/", "otro")
    else:
        expediente   = None
        bocg_url     = None
        tipo         = "otro"

    # Fallback: detectar tipo desde el texto
    if tipo == "otro":
        tipo = _tipo_desde_texto(texto_exp, titulo)

    # Si no tenemos bocg_url y conocemos el tipo + expediente
    if not bocg_url and expediente:
        _, _, parte = expediente.partition("/")
        num_bocg_tmp = str(int(parte))
        plantilla = _BOCG_URL.get(tipo)
        if plantilla:
            bocg_url = plantilla.format(num=num_bocg_tmp)

    # 2. num_bocg
    num_bocg = None
    if expediente:
        _, _, parte = expediente.partition("/")
        num_bocg = str(int(parte))

    # 3. Grupo proponente
    grupo_inicia = None
    if tipo in ("proyecto_ley", "convenio"):
        grupo_inicia = "Gobierno"
    else:
        m_grupo = _RE_GRUPO.search(texto_exp)
        if m_grupo:
            nombre_largo = m_grupo.group(1).strip()
            for fragmento, etiqueta in _GRUPOS:
                if fragmento in nombre_largo:
                    grupo_inicia = etiqueta
                    break
            if grupo_inicia is None:
                grupo_inicia = nombre_largo

    # 4. Punto
    punto = None
    m_punto = _RE_PUNTO.search(texto_sub)
    if m_punto:
        partes = m_punto.group(1).split()
        punto = partes[0].capitalize() + " " + partes[1]

    # 5. Enmienda a la totalidad
    es_enmienda_totalidad = bool(
        re.search(r"enmienda a la totalidad", texto_exp, re.IGNORECASE)
    )

    return {
        "tipo":                  tipo,
        "expediente":            expediente,
        "num_bocg":              num_bocg,
        "punto":                 punto,
        "grupo_inicia":          grupo_inicia,
        "bocg_url":              bocg_url,
        "es_enmienda_totalidad": es_enmienda_totalidad,
    }


if __name__ == "__main__":
    import json

    casos = [
        {
            "desc": "PNL – Grupo Popular",
            "informacion": {
                "textoExpediente": (
                    "Proposición no de Ley del Grupo Parlamentario Popular en el Congreso, "
                    "para garantizar la correcta implementación del Pacto Europeo...\n"
                    "162/000547"
                ),
                "textoSubGrupo": "",
                "titulo": "",
            },
            "esperado": {
                "tipo": "PNL", "expediente": "162/000547", "num_bocg": "547",
                "punto": None, "grupo_inicia": "PP",
                "bocg_url": "https://www.congreso.es/public_oficiales/L15/CONG/BOCG/D/BOCG-15-D-547.PDF",
                "es_enmienda_totalidad": False,
            },
        },
        {
            "desc": "Moción – Grupo Socialista, Punto 2",
            "informacion": {
                "textoExpediente": (
                    "Moción consecuencia de interpelación urgente del Grupo Parlamentario Socialista, "
                    "sobre...\n173/000089"
                ),
                "textoSubGrupo": "Punto 2. Texto del punto",
                "titulo": "",
            },
            "esperado": {
                "tipo": "mocion", "expediente": "173/000089", "num_bocg": "89",
                "punto": "Punto 2", "grupo_inicia": "PSOE",
                "bocg_url": None, "es_enmienda_totalidad": False,
            },
        },
        {
            "desc": "Proyecto de Ley – Gobierno",
            "informacion": {
                "textoExpediente": (
                    "Proyecto de Ley de Presupuestos Generales del Estado...\n121/000012"
                ),
                "textoSubGrupo": "",
                "titulo": "",
            },
            "esperado": {
                "tipo": "proyecto_ley", "expediente": "121/000012", "num_bocg": "12",
                "punto": None, "grupo_inicia": "Gobierno",
                "bocg_url": "https://www.congreso.es/public_oficiales/L15/CONG/BOCG/A/BOCG-15-A-12-1.PDF",
                "es_enmienda_totalidad": False,
            },
        },
    ]

    errores = 0
    for caso in casos:
        resultado = clasificar(caso["informacion"])
        esperado  = caso["esperado"]
        ok = resultado == esperado
        print(f"[{'OK' if ok else 'FALLO'}] {caso['desc']}")
        if not ok:
            errores += 1
            for k in esperado:
                if resultado.get(k) != esperado[k]:
                    print(f"       {k}: obtenido={resultado.get(k)!r}  esperado={esperado[k]!r}")
        else:
            print(f"       {json.dumps(resultado, ensure_ascii=False)}")

    print()
    print("Todos los tests pasaron." if errores == 0 else f"{errores} test(s) fallaron.")
