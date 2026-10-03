# ¿Estoy votando bien?

Un test de afinidad con el Congreso de los Diputados. Se te presentan propuestas **reales** votadas en el Pleno, **sin decirte quién las presentó**, y tú decides si las aprobarías, rechazarías o te abstendrías. Al final se compara lo que habrías votado con lo que votó cada grupo en esas mismas votaciones.

La idea es sencilla: que la gente pueda contrastar sus opiniones con los hechos (lo que cada grupo vota de verdad), sin la etiqueta del partido que las propone.

> **Aviso importante.** Los títulos y resúmenes de las propuestas los ha redactado **una inteligencia artificial** a partir de los textos oficiales y pueden contener errores. Los votos de los grupos son datos oficiales del Congreso. Si el resultado no te convence, o quieres comprobarlo, consulta la documentación oficial en [congreso.es](https://www.congreso.es). **Puedes estar votando a quien no te representa.** Esto no es una recomendación de voto. Lee también el [descargo de responsabilidad](#finalidad-y-descargo-de-responsabilidad).

## Qué datos usa

Las votaciones del Pleno de la **XV Legislatura** (desde el 17 de agosto de 2023, en curso). La versión actual incluye 2.122 propuestas votadas entre el 19 de septiembre de 2023 y el 30 de septiembre de 2026. No incluye las comisiones, solo el Pleno.

Fuentes: [datos abiertos del Congreso](https://www.congreso.es/es/opendata/votaciones) (votos por diputado), Boletín Oficial de las Cortes Generales (BOCG), Diario de Sesiones y BOE (textos).

## Cómo funciona

1. **Votos oficiales.** Se descargan de los datos abiertos del Congreso los votos de cada diputado en cada votación.
2. **Posición de cada grupo.** Un grupo vota *a favor*, *en contra* o *abstención* si esa opción supera el 50 % de sus miembros (contando también a quienes no votan). Si ninguna lo supera, el grupo está *dividido* y esa votación no cuenta para él.
3. **Qué se votaba.** Los datos oficiales de votación solo dicen «Punto 3» o «Enmienda 9». Se cruza cada votación con el orden del día para obtener el expediente y se localiza el texto en el BOCG, el Diario de Sesiones o el BOE.
4. **Títulos y resúmenes.** Una IA redacta el título y el resumen de lo que se vota en cada votación, con tres reglas: no nombrar grupos, partidos ni personas, no indicar el resultado, y describir solo lo que se vota. Los resúmenes con texto incompleto o reconstruido se marcan como *aproximados*.
5. **Test.** Una página estática sortea *N* propuestas, recoge tu respuesta y calcula la afinidad. Todo ocurre en tu navegador: nada se envía a ningún servidor.

### Cálculo de la afinidad

Para cada grupo: coincidencia exacta = 1 punto; abstención frente a sí o no = 0,5; sí frente a no = 0. Afinidad = puntos ÷ votaciones comparables. El diputado de Vox que pasó al Grupo Mixto cuenta como Vox; BNG, Coalición Canaria y UPN se muestran por separado, y los diputados del Mixto procedentes de Podemos y otros partidos ex-Sumar, como una entidad aparte.

### Qué se descarta y qué no

Solo se eliminan: (R1) votaciones sin título o resumen, (R2) votaciones sin voto de ningún grupo y (R3) votaciones repetidas con el mismo título y resumen (se conserva la última). **No se descarta nada por su resultado, por el tipo de iniciativa ni porque los grupos coincidan o discrepen.** Las enmiendas están incluidas y el test permite desactivarlas.

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `web/` | La aplicación estática (`index.html`) y su fichero de datos (`quiz.json`) |
| `scripts/` | Descarga de datos, cruce de expedientes, extracción de textos y generación del `quiz.json` |
| `data/` | CSV de votaciones, textos votados y resúmenes por lotes (formato jsonl) |

Más detalle técnico en [`CLAUDE.md`](CLAUDE.md); estado y tareas pendientes en [`PLAN_REHACER.md`](PLAN_REHACER.md).

## Probarlo en local

```bash
cd web
python3 -m http.server 8000
# abrir http://localhost:8000
```

(No se puede abrir el HTML con doble clic: el navegador bloquea la carga de `quiz.json`.)

### Regenerar los datos

Requiere Python 3 y `pypdf`.

```bash
python scripts/main.py                 # añade la última sesión publicada a data/votaciones.csv
python scripts/volcar_textos.py        # vuelca los textos votados (data/votaciones_texto/*.jsonl)
python scripts/volcar_resumenes.py     # vuelca títulos y resúmenes (data/resumenes/*.jsonl)
python scripts/generar_quiz.py         # genera web/quiz.json
```

## Limitaciones conocidas

- Los resúmenes no se han revisado uno a uno por una persona: se aplicaron comprobaciones automáticas y se leyó una muestra al azar.
- Hay votaciones sin texto oficial publicado (correcciones técnicas, votos particulares) que no aparecen en el test, y otras con texto incompleto (marcadas como aproximadas).
- El voto de un grupo en una enmienda a veces es táctico y no refleja su posición sobre el fondo.
- La afinidad mide coincidencia en las votaciones concretas del test. No resume el programa de nadie.
- BNG, Coalición Canaria y UPN tienen un solo diputado cada uno, así que su porcentaje varía mucho con pocas preguntas.

## Finalidad y descargo de responsabilidad

**Finalidad.** Este proyecto es una herramienta para entretener y concienciar. Quiere recordarle a cada ciudadano que votar en unas elecciones tiene consecuencias: lo que los grupos parlamentarios hacen después, votación a votación, en el Congreso de los Diputados. Nada más.

**Sin garantías.** Los autores del proyecto no dan ninguna garantía de exactitud, integridad ni corrección de los datos, los textos, los resúmenes ni los resultados que ofrece, ni de que sean adecuados para ningún fin. Aunque los votos proceden de datos oficiales, el tratamiento de esos datos, la selección de votaciones y la redacción de títulos y resúmenes (hecha con ayuda de IA) pueden contener errores. El servicio y el código se ofrecen «tal cual» y los autores no asumen responsabilidad por el uso que se haga de ellos.

**Juzga por ti mismo.** Corresponde a cada persona usar su propio criterio para valorar, con los datos oficiales del Congreso a la vista, si el grupo político que prefiere coincide de verdad con sus opiniones y con sus intereses. El resultado del test es un punto de partida para informarte, no una conclusión: antes de dar por buena una coincidencia (o una discrepancia), comprueba la votación en la documentación oficial en [congreso.es](https://www.congreso.es).

**Lo que no es.** No es una recomendación de voto, ni una encuesta, ni un análisis de los programas electorales. Mide únicamente coincidencia en las votaciones concretas que hayas respondido y no está vinculado al Congreso de los Diputados ni a ninguna formación política.

## Licencias

- **Código** (`scripts/`, `web/index.html`): [Apache 2.0](LICENSE).
- **Datos publicados** (`web/quiz.json`): [CC BY 4.0](LICENSE-DATOS). Atribución: Congreso de los Diputados (datos abiertos, BOCG y Diario de Sesiones) y BOE; títulos y resúmenes de los autores del proyecto, redactados con ayuda de IA.
- Los textos oficiales originales pertenecen al Congreso de los Diputados y al BOE y se rigen por sus propias condiciones de reutilización. El resto de ficheros de `data/` no tiene licencia declarada por ahora. Ver [`NOTICE`](NOTICE).

Gran parte del código (por no decir todo) y de los textos se ha generado con asistencia de IA.
