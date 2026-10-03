# Estado del proyecto y trabajo pendiente

## Hecho

- Descarga de las votaciones del Pleno de la XV Legislatura (141 sesiones, 2.175 votaciones) a `data/votaciones.csv`.
- Cruce de cada votación con su expediente a través del orden del día de la sesión (columna `expediente` de `data/votaciones.csv`, con los casos dudosos corregidos a mano).
- Localización del texto realmente votado en cada votación (punto de una PNL o moción, enmienda, dictamen, convenio...), con su fuente y un nivel de confianza (alta / media / baja / ninguna): `data/votaciones_texto/`.
- Redacción, con ayuda de IA, de título y resumen de 2.149 votaciones: `data/resumenes/`.
- Marcas en el CSV: `es_enmienda`, `es_enmienda_totalidad`, `resumen_aproximado`, `sin_texto`.
- Generador de la aplicación (`scripts/generar_quiz.py`) y prototipo web (`web/`).

## Pendiente

### Datos
- **Sesión 203** (2 de octubre de 2026, convalidación de dos reales decretos-ley de vivienda, expedientes 130/000055 y 130/000056): añadir al CSV cuando se publiquen sus votaciones en datos abiertos. Pasos: `python scripts/main.py`; texto votado desde el BOE; título y resumen; volcar con `scripts/volcar_textos.py` y `scripts/volcar_resumenes.py`; regenerar el quiz.
- **26 votaciones sin texto oficial publicado** (correcciones técnicas, votos particulares del Pacto de Estado de violencia de género): quedan fuera del test mientras no haya texto.
- **Unas 50 votaciones con confianza baja**, sobre todo transaccionales de comisión cuyo texto exacto no se publica en el BOCG. Pendiente de buscar en el Diario de Sesiones de Comisión.
- **Revisión de los resúmenes:** 520 están marcados como aproximados. Ampliar la revisión por muestreo y detectar más cruces votación-expediente erróneos comparando el texto de la votación con el texto votado.
- **Reales decretos-ley de las sesiones 129 y 136:** su expediente se asignó por la numeración correlativa; falta comprobarlo en la ficha de cada uno.
- **Mociones de la sesión 202** (expedientes 173/000194 a 196): sin texto hasta que se publique el BOCG.

### Aplicación web
- Probar la página en navegadores reales (móvil y escritorio).
- Etiquetas de los diputados individuales del Mixto: «UPN (Unión del Pueblo Navarro)», «Coalición Canaria», «BNG», con una nota de que son diputados individuales.
- Limitar el número de preguntas de una misma ley en un test corto.
- Publicación: GitHub Pages sirviendo solo `web/` (workflow de GitHub Actions).

### Documentación y licencias
- Decidir la licencia del resto de `data/` (hoy solo `web/quiz.json` tiene licencia declarada).
- Comprobar las condiciones de reutilización de los datos del Congreso antes de publicar.

## Notas para quien mantenga los datos

- Los «404» del BOCG suelen ser versiones corregidas con sufijo `-C1` (`BOCG-15-D-59-C1.PDF`).
- El número de sesión del Diario de Sesiones no coincide con el de la votación (por ejemplo, la sesión 192 es `DSCD-15-PL-198`).
- Los ficheros del BOCG a veces traen caracteres invisibles (U+200B) que rompen la división por enmiendas.
- Votaciones repetidas por empate: el mismo punto aparece votado varias veces el mismo día; el generador del test conserva solo la última.
- El cruce con el orden del día falla en las sesiones 2, 3, 9, 11, 73 y 171-177 (sin PDF o sin expedientes) y puede equivocarse en otras: los casos conocidos están corregidos a mano.
