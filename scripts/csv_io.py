#!/usr/bin/env python3
"""
Lectura y escritura del CSV de votaciones.
"""

import csv
from pathlib import Path

COLUMNAS = [
    "fecha", "sesion", "num_votacion", "expediente", "tipo", "punto",
    "titulo", "resumen", "sin_texto", "grupo_inicia", "es_enmienda_totalidad",
    "resultado", "si_total", "no_total", "abs_total",
    "PP_voto", "PSOE_voto", "Vox_voto", "Sumar_voto",
    "ERC_voto", "Junts_voto", "Bildu_voto", "PNV_voto",
    "MxSUMAR_voto", "MxBNG_voto", "MxCCa_voto", "MxUPN_voto", "MxVOX_voto",
]


def clave_unica(fila: dict) -> tuple:
    """Devuelve (str(sesion), str(num_votacion)) como clave de deduplicación."""
    return (str(fila.get("sesion", "")), str(fila.get("num_votacion", "")))


def leer_todo(ruta: str = "data/votaciones.csv") -> list[dict]:
    """Lee el CSV. Devuelve [] si no existe."""
    path = Path(ruta)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def escribir_fila(fila: dict, ruta: str = "data/votaciones.csv") -> None:
    """
    Añade o actualiza una fila en el CSV.
    Si el fichero no existe, lo crea con cabecera.
    Si ya existe una fila con el mismo (sesion, num_votacion), hace MERGE:
    solo sobreescribe los campos presentes en fila; el resto se conserva.
    Campos nuevos ausentes en filas existentes → cadena vacía.
    """
    path = Path(ruta)
    path.parent.mkdir(parents=True, exist_ok=True)

    existentes = leer_todo(ruta)
    clave = clave_unica(fila)

    nueva_lista = []
    reemplazado = False
    for row in existentes:
        if clave_unica(row) == clave:
            # Merge: partir de la fila existente y sobreescribir solo lo que viene
            merged = {col: row.get(col, "") for col in COLUMNAS}
            for col, val in fila.items():
                if col in COLUMNAS:
                    merged[col] = str(val)
            nueva_lista.append(merged)
            reemplazado = True
        else:
            nueva_lista.append({col: row.get(col, "") for col in COLUMNAS})
    if not reemplazado:
        nueva_lista.append({col: str(fila.get(col, "")) for col in COLUMNAS})

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNAS)
        writer.writeheader()
        writer.writerows(nueva_lista)


if __name__ == "__main__":
    RUTA_TEST = "data/test_csv_io.csv"

    # 1. Escribir dos filas
    escribir_fila({"sesion": 1, "num_votacion": 1, "titulo": "original", "PP_voto": "A favor"}, RUTA_TEST)
    escribir_fila({"sesion": 1, "num_votacion": 2, "titulo": "segunda"}, RUTA_TEST)

    # 2. Sobreescribir la primera
    escribir_fila({"sesion": 1, "num_votacion": 1, "titulo": "actualizado"}, RUTA_TEST)

    # 3. Leer y verificar
    filas = leer_todo(RUTA_TEST)
    assert len(filas) == 2, f"Esperaba 2 filas, hay {len(filas)}"
    assert filas[0]["titulo"] == "actualizado", f"Fila 1 no actualizada: {filas[0]['titulo']}"
    assert filas[1]["titulo"] == "segunda"
    print(f"OK — {len(filas)} filas, primera con titulo={filas[0]['titulo']!r}")

    # 4. Limpiar
    Path(RUTA_TEST).unlink()
    print("Fichero de prueba eliminado.")
