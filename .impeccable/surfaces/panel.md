# Surface brief: panel (Hoy, Marcaciones, Empleados, Configuración) + Excel

Scope: todo el panel local (`app/templates`, `app/static`) y el Excel exportado (`app/reports.py`).
Mode: Operate. Build path: code-led (pantalla de trabajo). Redesign: se conserva todo el
comportamiento, los datos y las rutas; se reemplaza el aspecto genérico actual.

Audiencia y tarea: secretaría (opera a diario: mira la llegada del personal, ABM, exporta el
Excel a fin de mes) y dirección (consulta de un vistazo quién vino y quién falta). 30-80
empleados. PC de escritorio en una oficina con luz diurna: tema claro.

Constraints: sin CDN ni fuentes externas; Jinja2 + HTMX; controles web estándar; nombre y logo
del colegio cargables desde el panel (todavía no entregados: nada inventado, estado vacío
elegante con "Cargá el nombre y el logo del colegio").

## Direction contract

THESIS: El panel es el libro de asistencia del personal hecho pantalla: la jornada de hoy se lee
como una franja horaria por persona, no como una tabla de eventos. Rechaza el dashboard genérico
de tarjetas con números grandes y la tabla gris con un acento azul.

OWN-WORLD: Mundo escolar argentino tomado solo en tipo, paleta, densidad y una firma. Shell en
verde pizarrón profundo (`#1d3a33`) con texto tiza (`#eef2ec`); fondo de trabajo blanco frío
apenas verdoso (`#f5f7f4`), superficies blancas; tinta de birome azul (`#2747b8`) para acciones,
enlaces, selección y foco. Estados: "En el colegio" verde (`#1f7a4a`), "Se retiró" pizarra
(`#4a5a68`), "Sin marcar" ámbar (`#a5650a`), peligro rojo (`#b42318`); siempre texto + color, nunca
color solo. Tipografía del sistema (Segoe UI Variable / Segoe UI / system-ui), una familia, escala
1.125, números tabulares en toda hora y cantidad. Densidad de planilla: filas de 44-48 px,
alineación estricta en columnas. Íconos SVG propios, trazo 1.5 px, un solo estilo.

STORY: Al abrir, la persona de secretaría ve la fecha de hoy y, en una sola línea, cuántos están
en el colegio, cuántos se retiraron y cuántos no marcaron; busca un nombre o filtra por estado y
ve su entrada, su salida y las horas. Dirección entiende la situación sin tocar nada. A fin de
mes se exporta un Excel que ya se ve como un documento del colegio.

FIRST VIEWPORT (Hoy, 1440x900): barra superior verde pizarrón: a la izquierda logo + nombre del
colegio (o el estado vacío), navegación Hoy · Marcaciones · Empleados · Configuración, a la
derecha el indicador del reloj (punto + "Reloj conectado · hace 3 s"). Debajo, en el fondo claro:
título con la fecha larga ("Martes 13 de octubre"), y a su derecha la hora actual. Luego una barra
de filtro segmentada que es a la vez el resumen: "Todos 42 · En el colegio 30 · Se retiraron 4 ·
Sin marcar 8", con el buscador por nombre/PIN a la derecha. El resto del viewport es la planilla:
Nombre (con PIN debajo, chico), Estado, Entrada, Salida, Horas, y la columna ancha de la jornada.
Acción primaria de la vista: ninguna destructiva; exportar vive en Marcaciones.

SIGNATURE: "La jornada" — cada fila tiene una franja horizontal sobre la escala de 07:00 a 19:00
(marcas de hora tenues en el encabezado de la columna): un tramo sólido de entrada a salida, o de
entrada a ahora (con el extremo abierto y pulsando suave) si sigue en el colegio; las marcaciones
intermedias como ticks finos; una línea vertical "ahora" cruza todas las filas. Cuando llega una
marcación nueva por el refresco, la hora de esa fila se "entinta": aparece con un relleno de
tinta azul que se desvanece en 1.2 s (ease-out exponencial), solo en esa celda. Respeta
`prefers-reduced-motion` (sin pulso ni entintado animado, solo el estado final).

FORM: Own-world escolar (pizarrón + tinta de birome), posición 1 de la lista propia. seed: none
(unavailable)

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Resto de las vistas (heredan el mundo)

- Marcaciones: filtros (desde, hasta, empleado) en una barra; columna "Tipo" con Entrada / Salida /
  Intermedia / Repetida según la misma regla del Excel (primera = entrada, última = salida,
  < 2 min = repetida); botón "Exportar a Excel" como acción primaria con ícono.
- Empleados: alta como formulario en línea arriba de la planilla (no modal), estados de comando
  como chips con texto, indicador del reloj ya está en la barra; "Últimos comandos" plegable.
- Configuración: nombre del colegio y logo (PNG/JPG/SVG, máx. 1 MB) con vista previa.
- Excel: hoja "Resumen por día" y "Detalle" con encabezado de documento: logo + nombre del
  colegio + "Asistencia del personal" + rango y fecha de emisión; fila de títulos verde pizarrón
  con texto blanco, filas cebra muy suaves, estado/observación en ámbar cuando corresponde,
  totales en negrita, configurado para imprimir (A4 horizontal, ajustar a 1 página de ancho,
  repetir títulos, pie con página N de M).

## Unresolved

- Nombre y logo reales del colegio (los carga el usuario desde Configuración).
