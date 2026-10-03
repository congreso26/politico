# Plan multiagente: rehacer títulos y resúmenes con el texto real

## Punto de partida
- Base: `git show HEAD:data/votaciones.csv` (commit 95f95e6). 2175 votaciones, solo la sesión 202 (21) con título/resumen buenos, 88 con `expediente`.
- Los datos de voto (grupos, totales, resultado) son oficiales y no se tocan.
- Descartar el trabajo del working tree: guardar `data/votaciones.csv` actual como `tmp/votaciones_borrador.csv` (referencia, no fuente) y hacer `git checkout HEAD -- data/votaciones.csv`.
- `data/textos.csv` NO es fiable (BOCG desalineado con la votación): se regenera.

## Hallazgos que fundamentan el plan
- Los "404" del BOCG son versiones corregidas con sufijo `-C1` (`BOCG-15-D-59-C1.PDF`).
- Texto de mociones: se publica en un BOCG-D posterior a la votación; la ficha de la iniciativa
  (`congreso.es/es/busqueda-de-iniciativas?...&_iniciativas_mode=mostrarDetalle&_iniciativas_legislatura=XV&_iniciativas_id=173/000003`)
  enlaza el BOCG exacto y el Diario de Sesiones (`DSCD-15-PL-N`).
- El orden del día (`tramit_pleno{fecha}_{N}.pdf`) da el nº de expediente de cada punto.
- Un PNL/moción por puntos = bloque «insta al Gobierno a: 1… N»; cada votación "Punto k" es el punto k.
- El BOCG de la moción indica además qué puntos se aprobaron (útil para validar).

## Fase 0 – Preparación (1 agente / yo, secuencial)
1. Restaurar el CSV base desde HEAD y respaldar el borrador.
2. Crear `data/iniciativas/` (un JSON por expediente) y `data/pdf_cache/` (no versionado).
3. Fijar el esquema de `data/iniciativas/{exp}.json`:
   `{expediente, tipo, bocg_urls[], fuente, texto_puntos: {"1": "...", ...}, texto_completo, estado: ok|sin_texto|error, notas}`.

## Fase 1 – Mapa votación → expediente (1 agente, secuencial; bloquea el resto)
- Para cada sesión (2–201): descargar `tramit_pleno{fecha}_{N}.pdf`, extraer `Núm. expte` y orden de los puntos, cruzar con las votaciones por orden y texto (`textoExpediente`, `textoSubGrupo`).
- Salida: columna `expediente` rellena en `votaciones.csv` + `tmp/mapa_validacion.csv` con las filas dudosas (sin cruce unívoco).
- Criterio de salida: ≥98 % de votaciones con expediente; las dudosas, listadas para revisión manual.
- Casos especiales: sesiones que abarcan varios días, votaciones "otro" (procedimentales) sin expediente, PNL "se vota en los términos de la enmienda transaccional" (el texto votado es la transaccional, no el original).

## Fase 2 – Localizar y descargar el texto real (agentes en paralelo por tipo)
Cada agente escribe solo `data/iniciativas/{exp}.json`; no toca el CSV.

| Agente | Alcance (expedientes) | Fuente | Notas |
|---|---|---|---|
| A. PNL | 162/ (~314 votaciones) | ficha → BOCG-D (probar `-C1`) | extraer bloque «insta…» partido en puntos; guardar también la enmienda transaccional si el texto dice «en los términos de» |
| B. Mociones | 173/ (~625) | ficha → BOCG-D posterior; fallback Diario de Sesiones | partir en puntos; registrar el texto realmente aprobado ("ha acordado lo siguiente") |
| C. Proyectos y proposiciones de ley | 121/, 122/, 120/ (~1000) | BOCG-A/B + informe de ponencia/dictamen | enmiendas: texto de la enmienda del Informe de la Ponencia/Comisión; votaciones "en bloque" y "resto de enmiendas" → descripción global |
| D. Convenios, RDL, otros | 110/, 130/, 140/, 152/, 156/, 250/ etc. (~230) | BOCG Cortes Generales / BOE | suelen bastar título + 2 líneas del objeto |

Reglas comunes a A–D:
- User-Agent `Mozilla/5.0`; caché de PDFs en `data/pdf_cache/`; máx. 4 peticiones simultáneas; reintentos con espera.
- Probar siempre `BOCG-15-X-N.PDF`, luego `-C1`, luego `-C2`; si falla, ir a la ficha de la iniciativa y seguir el enlace del BOCG.
- Extracción con `pypdf`; normalizar saltos de línea; quitar cabeceras «BOLETÍN OFICIAL…» y pies `cve:`.
- Validación automática por JSON: nº de puntos extraídos == nº de votaciones del expediente (si no, `estado: error` con nota).
- Cada agente devuelve un informe: ok / sin_texto / error por expediente, y las URLs que fallan.

## Fase 3 – Revisión de huecos (1 agente)
- Reintentar `error` y `sin_texto` con fuentes alternativas: Diario de Sesiones (`DSCD-15-PL-N`), búsqueda de publicaciones del Congreso, y, solo como último recurso, prensa (marcando `fuente: prensa`).
- Decidir `sin_texto=True` definitivo solo tras agotar las fuentes.

## Fase 4 – Redacción de títulos y resúmenes (agentes en paralelo, por bloques de sesiones)
- Un agente por bloque de ~20 sesiones (≈10 agentes). Entrada: filas del CSV + JSON de la iniciativa. No pueden usar nada fuera de esos textos.
- Reglas (de `RESUMENES.md`): anónimo (sin grupos, partidos ni parlamentarios), sin resultado, dos líneas, título descriptivo.
- Para votaciones por puntos: el título y resumen describen **ese punto** concreto, no la iniciativa entera (p. ej. «Cesar en los ataques a jueces y a la oposición»), con el nombre común de la iniciativa solo como contexto.
- Enmiendas a la totalidad: indicar que votar sí = devolver el proyecto.
- Votaciones en bloque: describir el conjunto de enmiendas por temas, sin inventar contenido.
- Escritura: cada agente genera `tmp/resumenes_{bloque}.csv` (sesion, num_votacion, titulo, resumen, sin_texto, fuente); solo yo hago el merge al CSV (evita conflictos de escritura).

## Fase 5 – Verificación (agentes independientes, no los redactores)
1. Automática: sin menciones a grupos/partidos/parlamentarios (regex + lista de nombres de `mixto_partidos.json` y diputados); resumen no vacío; longitud; coherencia punto↔votación.
2. Muestreo semántico: un agente revisor lee 10 % aleatorio (más los 50 de mayor riesgo: transaccionales, bloques, enmiendas) y compara resumen contra el texto fuente; tasa de error >3 % → se repite el bloque.
3. Contrastes oficiales: en mociones/PNL por puntos, comprobar que lo que el BOCG dice que se aprobó coincide con `resultado` del CSV.
4. Prueba de oro: reproducir a mano 5 casos conocidos (PNL inmigración punto 3; moción amnistía punto 3; sesión 202 completa).

## Fase 6 – Cierre
- Merge de los `tmp/resumenes_*.csv` en `data/votaciones.csv`, informe de cobertura (por tipo: ok, sin_texto, fuente), commit.
- Actualizar `CLAUDE.md` y `RESUMENES.md` con la nueva ruta de datos, el sufijo `-C1`, y el estado.
- Nueva versión de `scripts/` con los pasos 1–3 como código reutilizable (`mapa_expedientes.py`, `iniciativas.py`) para no depender de scripts de lote.

## Orden y paralelismo
Fase 0 → Fase 1 → Fase 2 (A, B, C, D en paralelo) → Fase 3 → Fase 4 (10 en paralelo) → Fase 5 (en paralelo) → Fase 6.

## Riesgos y decisiones abiertas
- Las ~1000 votaciones de enmiendas a leyes pueden no ser útiles para el test de afinidad (alta carga, poca señal): decidir si se resumen o se excluyen del quiz.
- Mociones muy recientes sin BOCG publicado: `sin_texto`.
- Volumen: ~2000 PDFs; respetar el servidor del Congreso (caché y concurrencia baja).
- Texto aprobado ≠ texto presentado en las transaccionales y en mociones modificadas: la fuente de verdad es el texto votado.

---
## Estado (pausado a petición del usuario para controlar gasto)
- Hecho: Fase 0 (CSV restaurado desde HEAD; borrador en tmp/votaciones_borrador.csv), Fase 1 (`scripts/mapa_expedientes.py`, 2050/2175 con expediente; dudosas en tmp/mapa_validacion.csv).
- Fase 2: textos votados en `data/votaciones_texto/*.jsonl`
  - auto_pnl_mociones (396), A_pnl (134), B1/B2_mociones (191/154), C1/C2_proyectos_ley (247/222): COMPLETOS.
  - C3_proyectos_ley (91 pendientes añadidas al mismo fichero), C4_proposiciones_ley (205), D1_resto (208), D2_resto (203): agentes lanzados tras corte por límite de uso. Si alguno quedó a medias, comparar con `tmp/agentes/{lote}.json` / `*_resto.json` y relanzar solo lo que falte.
- Pendiente (NO iniciado): revisión de huecos (fase 3; p. ej. mociones 173/000194-196 sesión 202 aún sin BOCG; correcciones técnicas sin texto; transaccionales rechazadas), redacción de títulos/resúmenes (fase 4; incluir las enmiendas con resumen de lo que pretenden y una marca para poder excluirlas del quiz), verificación (fase 5), cierre (fase 6).
- Cruces de expediente erróneos detectados por agentes: sesión 129 votaciones 3-4 (130/…), sesión 136 votaciones 87-88 (130/…), sesión 132 votación 1 (154/000002). Corregir en votaciones.csv al unir.
- Empates: mismo punto votado varias veces (p. ej. sesión 164 votaciones 3-5); decidir presentación.
- ACTUALIZACIÓN: C3, C4, D1 y D2 terminados. Fase 2 completa (todas las votaciones tienen línea en data/votaciones_texto/*.jsonl). Agentes avisan de más cruces erróneos con prefijo 140/ (declaraciones institucionales) y de expedientes SIN localizados (D1_resto.jsonl los trae corregidos). Pendiente: unir jsonl→votaciones.csv corrigiendo expedientes, fases 3-6.
- Volcado hecho: scripts/volcar_textos.py (columnas texto_votado, confianza_texto, fuente_texto en votaciones.csv; 157 expedientes corregidos en tmp/expedientes_corregidos.csv; huecos en tmp/huecos.csv). Siguiente: fase 4 (títulos/resúmenes).
- Fase 4 tanda 1 (PNL+mociones, 930) hecha y volcada (scripts/volcar_resumenes.py; data/resumenes/F4_*.jsonl). Pendiente tanda 2: proyectos/proposiciones de ley (enmiendas con resumen de lo que pretenden + marca es_enmienda), convenios, decretos, otros. Brief: tmp/agentes/BRIEF_F4.md (adaptar regla 4 para enmiendas).
- Fase 4 tanda 2 hecha y volcada (F4B/F4C). 2148 votaciones con título; 27 vacías (sin texto). es_enmienda=True marca enmiendas (excluibles del quiz). Pendiente: revisar 197/1 (texto_exp Defensa Nacional vs texto_votado vivienda), 27 vacías, fase 5 verificación semántica más amplia, fase 6 cierre (CLAUDE.md/RESUMENES.md, commit).
- Sesión 197 revisada: votación 1 = 122/000012 (Defensa Nacional, BOCG-B-24-1), corregida con título/resumen. Corregidos expedientes de decretos 129/3-4 → 130/000023 y 136/87-88 → 130/000024 (por secuencia numérica, no verificados en ficha).

---
## Seguimiento: sesión 203 (viernes 2/10/2026) – PENDIENTE DE VOTACIONES
- Orden del día publicado (3/10/2026): https://www.congreso.es/docu/tramit/LegXV/tramit_pleno20261002_203.pdf — punto único, convalidación de dos reales decretos-ley de vivienda:
  1. RDL 26/2026 (29/09/2026), protección de la función social de la vivienda y ampliación de la oferta de vivienda asequible — expte 130/000055 (BOE núm. 241, 30/09/2026). El orden del día indica "Derogado".
  2. RDL 27/2026 (29/09/2026), estabilidad de los contratos de arrendamiento de vivienda habitual — expte 130/000056 (BOE núm. 243, 01/10/2026). Indica "Derogado".
- Los datos de votación (ZIP opendata con voto por diputado) NO estaban publicados el 3/10/2026: el índice https://www.congreso.es/es/opendata/votaciones seguía en la sesión 202 (30/09/2026).
- Cómo añadirla al CSV cuando salga (a mano o con scripts existentes):
  1. `python scripts/main.py` (descarga la sesión más reciente del índice) o `--urls` con los JSON de la sesión 203; upsert por (sesion, num_votacion) en `data/votaciones.csv`.
  2. Expedientes: 130/000055 y 130/000056 (el orden del día resumido; los RDL no llevan "Núm. expte" en todos los PDF, comprobarlo).
  3. Texto votado: del BOE (RDL 26/2026 y 27/2026), confianza alta; puede haber también votaciones de "tramitación como proyecto de ley" si el RDL se convalida (parece derogado: no habría).
  4. `python scripts/volcar_textos.py`-equivalente: añadir línea en `data/votaciones_texto/` (p. ej. `s203.jsonl`) y `data/resumenes/s203.jsonl`, luego `python scripts/volcar_textos.py && python scripts/volcar_resumenes.py`.
  5. Recalcular `es_enmienda` (False aquí) y comprobar anonimato/resultado (si resultado "Derogado", la votación de convalidación fue rechazada).
- Estado general: ver sección "Estado" arriba. Siguiente tras esto: verificación más amplia (texto_exp vs texto_votado de las 2175, detectar más cruces como el de la 197), cierre (CLAUDE.md/RESUMENES.md, commit).
