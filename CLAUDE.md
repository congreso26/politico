# Votaciones del Pleno del Congreso: datos y test de afinidad

Proyecto que descarga las votaciones del Pleno del Congreso de los Diputados (XV Legislatura), las enriquece con el texto votado, un título y un resumen anónimos redactados con ayuda de IA, y las publica como un test de afinidad estático (`web/`). Ver `README.md` para el planteamiento y `PLAN_REHACER.md` para el estado y los pendientes.

## Principios

- **Los votos son datos oficiales; los títulos y resúmenes son interpretación** de una IA a partir del texto. Esto debe quedar siempre claro en la web y en la documentación.
- **Neutralidad:** no se elimina ninguna votación por su resultado, por su tipo ni porque los grupos coincidan o discrepen. Las reglas de eliminación del generador del test son únicas y están documentadas (ver más abajo).
- **Anonimato de los textos:** títulos y resúmenes no mencionan grupos, partidos ni personas, y no dicen si la propuesta se aprobó o rechazó.
- **Privacidad:** el repositorio no debe contener datos personales de los autores (nombres, correos, rutas locales). Identidad de commits: la configurada en el repositorio (no la del sistema).

## Reglas de datos

### Posición de un grupo
- Un grupo vota X si **más del 50 % de sus miembros** vota X.
- El denominador son **todos los miembros del grupo** que aparecen en la votación, **incluidos** los «No vota».
- Si ninguna opción supera el 50 % → **Dividido**.
- El Grupo Mixto es heterogéneo: se desglosa por partido (`data/mixto_partidos.json`). Un diputado que pasó al Mixto desde otro grupo cuenta con su grupo de origen (caso conocido: un diputado de Vox).

### Resultado
`afavor > enContra` vale para mayoría simple. Las leyes orgánicas (votación final) y otras votaciones cualificadas necesitan otra regla; pendiente de revisar.

### Votaciones por puntos
Una iniciativa votada por puntos o bloques genera varias votaciones con el mismo `textoExpediente` y distinto `textoSubGrupo` («Punto 3», «Enmienda 9», «Resto de las enmiendas»). Cada votación es una fila del CSV y su texto votado es el de ese punto o enmienda.

## Fuentes

### Votaciones
- Índice: `https://www.congreso.es/es/opendata/votaciones` (solo muestra la sesión más reciente con todos sus enlaces).
- Por sesión hay un ZIP con todas las votaciones:
  `https://www.congreso.es/webpublica/opendata/votaciones/Leg15/Sesion{N}/{AAAAMMDD}/VOT_{timestamp}.zip`
  El timestamp no es predecible: sale del HTML del índice. Dentro: `sesion{N}votacion{M}.json|xml|pdf|png`.
- Para fechas pasadas, el opendata acepta `targetDate=DD/MM/AAAA` (lo usa `scripts/descargar_legislatura.py`).
- Usar un `User-Agent` de navegador (`curl -A "Mozilla/5.0"`).

Estructura del JSON de una votación:
```json
{
  "informacion": {"sesion": 202, "numeroVotacion": 1, "fecha": "30/9/2026",
    "titulo": "Proposiciones no de Ley.", "textoExpediente": "Proposición no de Ley del Grupo ...",
    "tituloSubGrupo": "", "textoSubGrupo": "Votación separada por puntos. Punto 1.", "votacionesConjuntas": []},
  "totales": {"asentimiento": "No", "presentes": 346, "afavor": 137, "enContra": 175, "abstenciones": 34, "noVotan": 4},
  "votaciones": [{"asiento": "6", "diputado": "Apellidos, Nombre", "grupo": "GSUMAR", "voto": "No"}]
}
```
Valores de `voto`: `Sí`, `No`, `Abstención`, `No vota`.

| Código | Grupo |
|---|---|
| GP | PP |
| GS | PSOE |
| GVOX | Vox |
| GSUMAR | Sumar |
| GR | ERC |
| GJxCAT | Junts |
| GEH Bildu | Bildu |
| GV (EAJ-PNV) | PNV |
| GMx | Mixto |

En una enmienda a la totalidad de devolución, votar «sí» significa devolver el proyecto al Gobierno.

### Texto de las iniciativas
- **Orden del día resumido** (da el número de expediente de cada punto): `https://www.congreso.es/docu/tramit/LegXV/tramit_pleno{AAAAMMDD}_{N}.pdf` (puede no existir para algunas sesiones; los reales decretos-ley no siempre llevan «Núm. expte»).
- **Ficha de la iniciativa** (enlaza el BOCG y el Diario de Sesiones exactos, con página):
  `https://www.congreso.es/es/busqueda-de-iniciativas?p_p_id=iniciativas&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_iniciativas_mode=mostrarDetalle&_iniciativas_legislatura=XV&_iniciativas_id=173/000003`
- **BOCG Congreso:** serie D (PNL, mociones) `…/CONG/BOCG/D/BOCG-15-D-{n}.PDF`; serie A (proyectos de ley, sufijos `-1` proyecto, `-2`/`-3` enmiendas, `-4`/`-5` ponencia y dictamen…) `…/CONG/BOCG/A/BOCG-15-A-{n}-{k}.PDF`; serie B (proposiciones de ley) `…/CONG/BOCG/B/BOCG-15-B-{n}-{k}.PDF`. Base: `https://www.congreso.es/public_oficiales/L15`.
- **BOCG Cortes Generales** (convenios): `…/CORT/BOCG/A/BOCG-15-CG-A-{n}.PDF`.
- **Diario de Sesiones del Pleno:** `…/CONG/DS/PL/DSCD-15-PL-{n}.PDF` (el número no coincide con el de la sesión).
- **Los «404» del BOCG suelen ser versiones corregidas con sufijo `-C1`** (`BOCG-15-D-59-C1.PDF`).
- Prefijos de expediente: `162/` PNL, `173/` moción consecuencia de interpelación, `121/` proyecto de ley, `122/` proposición de ley, `110/` convenio, `130/` real decreto-ley, `102/` reforma constitucional, `410/` reforma del Reglamento, `140/` declaración institucional (no es una votación del Pleno ordinaria).
- Extracción de texto de PDF: `pypdf` (no hay `pdftotext`). Ojo con caracteres invisibles (U+200B) en algunos BOCG.
- En las PNL y mociones el texto votado está en el bloque «El Congreso de los Diputados insta al Gobierno a: 1… 2…».
- El texto final de una **moción** se publica en un BOCG-D unos días después de la votación (con el texto presentado, las enmiendas y el texto acordado).

## Flujo de trabajo

1. **Descarga:** `python scripts/main.py` (sesión más reciente) o `python scripts/main.py --urls URL1 URL2 …`; `scripts/descargar_legislatura.py` recorre día a día toda la legislatura. Escribe en `data/votaciones.csv` con upsert por (`sesion`, `num_votacion`).
2. **Expediente:** `main.py` cruza cada votación con el orden del día (`orden_dia.py`). Falla donde no hay PDF o hay ambigüedad (sesiones 2, 3, 9, 11, 73 y 171-177 en la carga histórica); los casos conocidos están corregidos a mano en la columna `expediente` de `votaciones.csv`.
3. **Texto votado:** `scripts/iniciativas.py` resuelve ficha → BOCG → bloque dispositivo y puntos. Los casos que no resuelve solos se completan a mano o con asistencia. Resultado en `data/votaciones_texto/*.jsonl` (`texto_votado`, `fuente_url`, `confianza`: alta / media / baja / ninguna). Se vuelca con `python scripts/volcar_textos.py`.
4. **Título y resumen:** `data/resumenes/*.jsonl` (`titulo`, `resumen`, `aproximado`), volcado con `python scripts/volcar_resumenes.py`. Reglas: anónimo, sin resultado, máximo dos frases, descripción de lo que se vota en esa votación concreta. En enmiendas: qué pretende cambiar. `resumen_aproximado` marca textos cortados o con confianza no alta.
5. **Test:** `python scripts/generar_quiz.py` genera `web/quiz.json`. La página `web/index.html` es estática (sin servidor).

### Reglas de eliminación de `generar_quiz.py`
Únicas y en este orden: **R1** sin título o sin resumen; **R2** sin voto de ningún grupo; **R3** mismo título y mismo resumen (votaciones repetidas): se conserva la última en el orden del CSV. No se elimina nada por tipo (las enmiendas entran), resultado, grupos divididos, resumen aproximado ni confianza. El informe de cada ejecución y el campo `descartes` del JSON cuentan cuántas elimina cada regla.

### Módulos (`scripts/`)
| Script | Función |
|---|---|
| `sesiones.py` | Scraping del índice de opendata → lista de URLs JSON |
| `votaciones.py` | Descarga y parseo de cada JSON de votación |
| `orden_dia.py` | Descarga y parseo del PDF del orden del día |
| `expedientes.py` | Clasifica tipo, proponente y punto |
| `grupos.py` | Posición por grupo; desglosa el Mixto con `data/mixto_partidos.json` |
| `bocg.py` | Descarga PDF del BOCG y extrae el texto relevante |
| `csv_io.py` | Lectura/escritura del CSV (columnas y upsert) |
| `main.py`, `descargar_legislatura.py` | Orquestadores |
| `iniciativas.py` | Ficha de la iniciativa → BOCG → texto y puntos |
| `volcar_textos.py`, `volcar_resumenes.py` | Vuelcan los jsonl al CSV |
| `generar_quiz.py` | Genera `web/quiz.json` |

### Columnas del CSV
`fecha, sesion, num_votacion, expediente, tipo, punto, titulo, resumen, resumen_aproximado, sin_texto, texto_votado, confianza_texto, fuente_texto, grupo_inicia, es_enmienda, es_enmienda_totalidad, resultado, si_total, no_total, abs_total, PP_voto, PSOE_voto, Vox_voto, Sumar_voto, ERC_voto, Junts_voto, Bildu_voto, PNV_voto, MxSUMAR_voto, MxBNG_voto, MxCCa_voto, MxUPN_voto, MxVOX_voto`

## Licencias
Código: Apache 2.0 (`LICENSE`). `web/quiz.json`: CC BY 4.0 con atribución a las fuentes (`LICENSE-DATOS`). El resto de `data/` sin licencia declarada. Ver `NOTICE`. Los scripts llevan la cabecera `# SPDX-License-Identifier: Apache-2.0`.

## Fuera de alcance
Comisiones (solo Pleno).
