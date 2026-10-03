# Resumen de votaciones del Congreso de los Diputados

Herramienta para generar un resumen legible de las votaciones del Pleno del Congreso (XV Legislatura, año 2026), con título, resumen, proponente y posición de cada grupo parlamentario.

## Formato de salida de cada votación

1. **Título descriptivo** de lo que se vota (no el título burocrático del expediente).
2. **Resumen de dos líneas** con los puntos clave.
3. **Proponente**: grupo parlamentario autor (o Gobierno en proyectos de ley y convenios).
4. **Resultado**: Aprobada / Rechazada con totales (sí / no / abstenciones).
5. **Grupos** clasificados en A favor / En contra / Abstención / Dividido.

### Regla de posición de grupo
- Un grupo vota X si **más del 50 % de sus miembros** vota X.
- El denominador son **todos los miembros del grupo** que aparecen en la votación, **incluidos** los "No vota".
- Si ninguna opción supera el 50 % → **Dividido**.
- El Grupo Mixto es heterogéneo (Podemos, BNG, CC, UPN, Compromís…); su posición agregada dice poco. Pendiente: valorar desglosarlo por partido.

### Votaciones por puntos
Una iniciativa votada por puntos o bloques genera varias votaciones con el mismo `textoExpediente` y distinto `textoSubGrupo`. En el prototipo se agruparon en una sola entrada con una tabla por punto.

## Fuentes de datos

### Votaciones (datos oficiales, fiables)
- Índice: https://www.congreso.es/es/opendata/votaciones (HTML, contiene enlaces a la última sesión).
- Por sesión hay un ZIP con todas las votaciones:
  `https://www.congreso.es/webpublica/opendata/votaciones/Leg15/Sesion{N}/{AAAAMMDD}/VOT_{timestamp}.zip`
  El timestamp no es predecible: hay que sacarlo del HTML del índice. Dentro: `sesion{N}votacion{M}.json|xml|pdf|png`.
- Usar `curl -A "Mozilla/5.0"`.

Estructura del JSON:
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

Códigos de grupo → nombre corto:
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

El proponente se extrae de `textoExpediente` ("del Grupo Parlamentario X"); en convenios y proyectos de ley es el Gobierno. En una enmienda a la totalidad, el proponente es el grupo que la presenta, y votar "sí" significa devolver el proyecto.

### Contenido de las iniciativas (para los resúmenes)
- **Orden del día resumido** con número de expediente y referencia al BOCG:
  `https://www.congreso.es/docu/tramit/LegXV/tramit_pleno{AAAAMMDD}_{N}.pdf` (N = número de sesión; una sesión puede abarcar varios días).
- **BOCG Congreso** (PNL en serie D, proyectos de ley en serie A):
  `https://www.congreso.es/public_oficiales/L15/CONG/BOCG/D/BOCG-15-D-{num}.PDF`
  `https://www.congreso.es/public_oficiales/L15/CONG/BOCG/A/BOCG-15-A-{num}-1.PDF`
- **BOCG Cortes Generales** (convenios internacionales):
  `https://www.congreso.es/public_oficiales/L15/CORT/BOCG/A/BOCG-15-CG-A-{num}.PDF`
- Prefijos de expediente: `162/` PNL, `173/` moción consecuencia de interpelación, `121/` proyecto de ley, `122/` proposición de ley, `110/` convenio internacional.
- En las PNL, lo importante está al final del texto: el bloque que empieza por «El Congreso de los Diputados insta al Gobierno a: …».
- Extracción de texto de PDF: `pypdf` (no hay `pdftotext` instalado).

### Problemas conocidos
- Algunos PDF del BOCG devuelven 404 (p. ej. D-518) aunque estén citados en el orden del día.
- El texto final de las **mociones** (173/) no está en el BOCG el día de la votación; se publica más tarde. Mientras tanto, la única fuente es la prensa, menos fiable: indicar en la salida qué resúmenes vienen de prensa.
- Los resúmenes los genera un LLM a partir del texto: **los votos son datos oficiales; los resúmenes son interpretación**.

## Prototipo (ejemplo validado, sesión 202 del 30/09/2026)

Script mínimo de agregación usado en el prototipo:
```python
import json, glob, re, collections
N = {'GP':'PP','GS':'PSOE','GVOX':'Vox','GSUMAR':'Sumar','GR':'ERC','GJxCAT':'Junts',
     'GEH Bildu':'Bildu','GV (EAJ-PNV)':'PNV','GMx':'Mixto'}
for f in sorted(glob.glob('s/*.json'), key=lambda f: int(re.search(r'votacion(\d+)', f).group(1))):
    d = json.load(open(f)); t = d['totales']
    g = collections.defaultdict(collections.Counter)
    for v in d['votaciones']:
        g[N[v['grupo']]][v['voto']] += 1
    pos = {'A favor': [], 'En contra': [], 'Abstención': [], 'Dividido': []}
    lab = {'Sí': 'A favor', 'No': 'En contra', 'Abstención': 'Abstención'}
    for grupo, c in g.items():
        tot = sum(c.values())
        win = [o for o in lab if c[o] > tot / 2]
        pos[lab[win[0]] if win else 'Dividido'].append(grupo)
    resultado = 'Aprobada' if t['afavor'] > t['enContra'] else 'Rechazada'
```
Nota: el resultado `afavor > enContra` vale para mayoría simple. Las leyes orgánicas (votación final) y otras votaciones cualificadas necesitan otra regla; revisarlo.

Ejemplo de salida aprobado por el usuario:

> ### Aplicación del Pacto Europeo de Migración y Asilo
> Pide al Gobierno aprobar con urgencia las reformas para adaptar el Pacto, informar a las Cortes de cómo va su aplicación y reforzar los medios para el triaje y los procedimientos de asilo en frontera. También le pide votar a favor del nuevo Reglamento europeo de Retornos.
> - **Propone:** PP · **Resultado:** ❌ Rechazada (137 sí / 175 no / 34 abst.)
> - **A favor:** PP · **En contra:** PSOE, Sumar, ERC, Junts, Bildu, PNV, Mixto · **Abstención:** Vox

Las 14 votaciones de esa sesión cubren PNL, mociones por puntos, una enmienda a la totalidad y convenios. Es un buen caso de prueba.

## Herramienta construida (scripts/)

### Uso
```bash
# Sesión del día (automático):
python scripts/main.py

# Sesión pasada (manual, pegar URLs del índice):
python scripts/main.py --urls URL1 URL2 ...

# Opciones: --limit N  --out data/otro.csv
```

### Módulos
| Script | Función |
|---|---|
| `sesiones.py` | Scraping del índice de opendata → lista de URLs JSON |
| `votaciones.py` | Descarga y parseo de cada JSON de votación |
| `orden_dia.py` | Descarga tramit_pleno{fecha}_{N}.pdf → expedientes + BOCG URLs |
| `expedientes.py` | Clasifica tipo, proponente, punto; usa orden_dia cuando disponible |
| `grupos.py` | Agrega votos por grupo; desglosa Mixto con mixto_partidos.json |
| `bocg.py` | Descarga PDF del BOCG, extrae texto relevante con pypdf |
| `csv_io.py` | Lectura/escritura del CSV con upsert por (sesion, num_votacion) |
| `main.py` | Orquestador; `titulo` y `resumen` se dejan vacíos para rellenar |

### Hallazgos técnicos
- El índice opendata (`/es/opendata/votaciones`) solo muestra la sesión más reciente con todos sus links JSON. No hay API para sesiones anteriores.
- El expediente (162/000814) **no está en el JSON de votación**; hay que extraerlo del PDF del orden del día (`tramit_pleno{AAAAMMDD}_{N}.pdf`).
- Los timestamps de los ficheros JSON son impredecibles (no siguen patrón horario fijo).
- El Grupo Mixto se desglosa usando `data/mixto_partidos.json` (generado por `descargar_mixto.py`).
- Mociones (173/): sin BOCG el día de la votación → texto vacío.
- BOCG-15-D-518 devuelve 404 aunque está citado en el orden del día.

### Columnas del CSV
`fecha, sesion, num_votacion, expediente, tipo, punto, titulo*, resumen*, resumen_aproximado, sin_texto, texto_votado, confianza_texto, fuente_texto, grupo_inicia, es_enmienda, es_enmienda_totalidad, resultado, si_total, no_total, abs_total, PP_voto, PSOE_voto, Vox_voto, Sumar_voto, ERC_voto, Junts_voto, Bildu_voto, PNV_voto, MxSUMAR_voto, MxBNG_voto, MxCCa_voto, MxUPN_voto, MxVOX_voto`

*`titulo` y `resumen` se rellenan manualmente con ayuda del LLM a partir del texto del BOCG.

## Flujo de textos y resúmenes (rehecho: datos de la XV Legislatura completa)
1. `scripts/mapa_expedientes.py`: expediente de cada votación, cruzando con el orden del día (`data/mapa_expedientes.csv`). Falla en sesiones sin PDF (2, 3, 9, 11, 73, 171-177) y puede cruzar mal; corregidos a mano los casos conocidos.
2. `scripts/iniciativas.py`: ficha de la iniciativa → BOCG → texto y puntos. Los «404» del BOCG son versiones corregidas con sufijo `-C1`.
3. Texto realmente votado por votación: `data/votaciones_texto/*.jsonl` (texto_votado, fuente_url, confianza alta/media/baja/ninguna), volcado con `scripts/volcar_textos.py`.
4. Títulos y resúmenes: `data/resumenes/*.jsonl`, volcado con `scripts/volcar_resumenes.py`. Anónimos, sin resultado, 2 frases. `resumen_aproximado` = texto cortado o confianza no alta.
5. `es_enmienda` marca enmiendas (se pueden excluir del quiz). Las enmiendas a la totalidad no entran en esa marca.
6. `scripts/generar_quiz.py` → `web/quiz.json` (app estática en cliente). Reglas de eliminación, únicas y en este orden: R1 sin título o sin resumen; R2 sin voto de ningún grupo; R3 mismo título y mismo resumen (votaciones repetidas): se conserva la última en el orden del CSV. No se elimina nada por tipo (las enmiendas entran), resultado, grupos divididos, resumen aproximado ni confianza. El informe de cada ejecución y el JSON (`descartes`) cuentan cuántas elimina cada regla.
7. Estado y pendientes: `PLAN_REHACER.md` (sesión 203 sin votaciones publicadas a 3/10/2026; 26 votaciones sin texto: correcciones técnicas y votos particulares).

## Pendiente / decisiones abiertas
- **Rellenar títulos y resúmenes** de las 21 votaciones de la sesión 202 (siguiente paso inmediato).
- **Sesiones pasadas**: descubrimiento de URLs manual (estrategia C). Mejorar en el futuro.
- **Formato de entrega final** (web con filtros, app móvil, etc.): sin decidir.
- **Cobertura**: solo sesión actual por ahora. Para cubrir 2026 completo, habría que ejecutar la herramienta día a día o encontrar forma de recuperar sesiones pasadas.
- **Comisiones**: fuera del alcance (solo Pleno).
