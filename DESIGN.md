---
name: mini-asistencia
description: El libro de asistencia del personal del colegio, hecho pantalla. Panel local + Excel.
colors:
  pizarra: "#1d3a33"
  tiza: "#eef2ec"
  tiza-suave: "#b9cbc1"
  fondo: "#f5f7f4"
  superficie: "#ffffff"
  superficie-2: "#edf1ed"
  superficie-presionada: "#e1e8e2"
  fila-hover: "#f9fbf8"
  borde: "#d6ded7"
  borde-fuerte: "#b3c0b6"
  borde-control: "#7f8f84"
  borde-control-hover: "#5f7166"
  texto: "#1b2420"
  suave: "#566159"
  placeholder: "#6b756f"
  tinta: "#2747b8"
  tinta-hover: "#1f3a99"
  tinta-activa: "#182e7a"
  tinta-clara: "#aebdf5"
  tinta-fill: "rgb(39 71 184 / 0.28)"
  tinta-12: "rgb(39 71 184 / 0.1)"
  verde: "#1f7a4a"
  pizarra-estado: "#4a5a68"
  ambar: "#a5650a"
  rojo: "#b42318"
  verde-fondo: "#e8f3ec"
  ambar-fondo: "#fbf3e3"
  rojo-fondo: "#fdeceb"
  rojo-presionado: "#f9d9d6"
  verde-borde: "#a9d3b8"
  ambar-borde: "#e3cf9f"
  rojo-borde: "#dca29c"
  reloj-conectado: "#6fd49b"
  reloj-sin-contacto: "#f2b84b"
  reloj-nunca: "#8fa398"
typography:
  headline:
    fontFamily: "Segoe UI Variable Text, Segoe UI Variable, Segoe UI, system-ui, -apple-system, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.602rem"
    fontWeight: 700
    lineHeight: 1.2
  hora:
    fontFamily: "Segoe UI Variable Text, Segoe UI Variable, Segoe UI, system-ui, sans-serif"
    fontSize: "1.266rem"
    fontWeight: 600
    fontFeature: "tnum"
  title:
    fontFamily: "Segoe UI Variable Text, Segoe UI Variable, Segoe UI, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 650
    lineHeight: 1.2
  body-fila:
    fontFamily: "Segoe UI Variable Text, Segoe UI Variable, Segoe UI, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.25
    fontFeature: "tnum"
  body:
    fontFamily: "Segoe UI Variable Text, Segoe UI Variable, Segoe UI, system-ui, sans-serif"
    fontSize: "0.889rem"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tnum"
  label:
    fontFamily: "Segoe UI Variable Text, Segoe UI Variable, Segoe UI, system-ui, sans-serif"
    fontSize: "0.79rem"
    fontWeight: 600
    lineHeight: 1.25
    fontFeature: "tnum"
rounded:
  tramo: "3px"
  numero: "4px"
  sm: "6px"
  segmento: "7px"
  md: "8px"
  grupo: "10px"
  lg: "12px"
  pill: "13px"
  disco: "50%"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  celda: "14px"
  gutter: "32px"
  gutter-tablet: "24px"
  gutter-movil: "16px"
components:
  button:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.texto}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "40px"
  button-hover:
    backgroundColor: "{colors.superficie-2}"
  button-active:
    backgroundColor: "{colors.superficie-presionada}"
  button-primario:
    backgroundColor: "{colors.tinta}"
    textColor: "{colors.superficie}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "40px"
  button-primario-hover:
    backgroundColor: "{colors.tinta-hover}"
  button-primario-active:
    backgroundColor: "{colors.tinta-activa}"
  button-ghost:
    textColor: "{colors.tinta}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "40px"
  button-ghost-hover:
    backgroundColor: "{colors.tinta-12}"
    textColor: "{colors.tinta-hover}"
  button-peligro:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.texto}"
  button-peligro-hover:
    backgroundColor: "{colors.rojo-fondo}"
    textColor: "{colors.rojo}"
  button-chico:
    typography: "{typography.label}"
    padding: "0 10px"
    height: "32px"
  input:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.texto}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "0 12px"
    height: "40px"
  input-disabled:
    backgroundColor: "{colors.superficie-2}"
    textColor: "{colors.suave}"
  nav-item:
    textColor: "{colors.tiza-suave}"
    rounded: "{rounded.md}"
    padding: "0 14px"
    height: "40px"
  nav-item-actual:
    backgroundColor: "rgb(238 242 236 / 0.16)"
    textColor: "{colors.superficie}"
  segmentos:
    backgroundColor: "{colors.superficie-2}"
    rounded: "{rounded.grupo}"
    padding: "3px"
  segmento:
    textColor: "{colors.suave}"
    typography: "{typography.body}"
    rounded: "{rounded.segmento}"
    padding: "0 14px"
    height: "32px"
  segmento-elegido:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.texto}"
  chip-estado:
    backgroundColor: "{colors.superficie}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0 10px 0 9px"
    height: "26px"
  planilla:
    backgroundColor: "{colors.superficie}"
    rounded: "{rounded.lg}"
  planilla-encabezado:
    backgroundColor: "{colors.superficie-2}"
    textColor: "{colors.suave}"
    typography: "{typography.label}"
    padding: "0 14px"
    height: "44px"
  planilla-fila:
    typography: "{typography.body}"
    padding: "0 14px"
    height: "46px"
  hoy-fila:
    typography: "{typography.body-fila}"
    padding: "0 14px"
    height: "48px"
  formulario-en-linea:
    backgroundColor: "{colors.superficie}"
    rounded: "{rounded.lg}"
    padding: "20px 24px"
  barra:
    backgroundColor: "{colors.pizarra}"
    textColor: "{colors.tiza}"
    height: "68px"
  tramo:
    backgroundColor: "{colors.verde}"
    rounded: "{rounded.tramo}"
    height: "10px"
---

# Design System: mini-asistencia

## Overview

**Creative North Star: "El libro de asistencia hecho pantalla"**

El panel es el libro de asistencia del personal de un colegio argentino, no un dashboard. La
jornada de hoy se lee como una franja horaria por persona sobre la escala de 07:00 a 19:00, en una
planilla densa y alineada, como la hoja de un libro de firmas. El mundo escolar entra solo por
cuatro vías: la paleta (barra en verde pizarrón con texto tiza, tinta de birome azul para todo lo
que se puede tocar), la densidad de planilla, el lenguaje de escuela y una firma, "La jornada".
Nada de ilustraciones, texturas de pizarrón ni tipografías "manuscritas".

La superficie de trabajo es clara (oficina con luz diurna, tema claro único) y plana: blanco frío
apenas verdoso, tarjetas y planillas blancas con un borde fino, sin sombras. La profundidad la da
el contraste de tono, no la elevación. El color de estado (verde, pizarra, ámbar, rojo) siempre
acompaña a un texto; nunca comunica solo. Una única familia del sistema, escala 1.125 y números
tabulares en todas partes, porque la materia prima son horas y cantidades.

El Excel exportado es el mismo mundo trasladado al papel: encabezado de documento con logo y
nombre del colegio, fila de títulos en verde pizarrón, cebra muy suave y listo para imprimir.
Rechazos confirmados por la dirección: el dashboard genérico de tarjetas con números grandes y la
tabla gris con un acento azul.

**Key Characteristics:**
- Shell verde pizarrón + texto tiza; trabajo sobre blanco frío; tinta azul solo para interacción.
- Planilla densa (filas de 46-48 px), columnas estrictas, números tabulares.
- Estado = punto o color + texto, siempre.
- Plano: bordes finos de 1 px y tono; cero sombras proyectadas.
- Una firma: "La jornada" (franja horaria por persona) y su gesto vivo, el entintado.
- Movimiento mínimo, ease-out exponencial, con alternativa completa para movimiento reducido.

## Colors

Una paleta de escuela: verde pizarrón y tiza para el marco, tinta de birome para la acción, y
cuatro colores de estado que nunca aparecen sin su palabra.

### Primary
- **Tinta de birome** (tinta): el único color de interacción. Botón primario, enlaces, foco
  (contorno de 2 px), selección de texto, caret y `accent-color`, la línea y el triángulo "ahora"
  de La jornada, y el relleno del entintado. Hover y presión oscurecen la misma tinta
  (tinta-hover, tinta-activa). Sobre la barra oscura el foco usa **Tinta clara** (tinta-clara).
- **Tinta translúcida** (tinta-12, tinta-fill): fondo de hover de los botones fantasma y del
  plegable "Últimos comandos" (10 %); relleno inicial del entintado (28 %).

### Secondary
- **Verde pizarrón** (pizarra): la barra superior, la vista previa de la barra en Configuración,
  el ícono de la app y la fila de títulos del Excel. Es el marco, nunca un botón.
- **Tiza** (tiza): texto sobre el pizarrón (10.9:1), subrayado del ítem de navegación actual, fondo
  del disco del logo y del enlace "Saltar al contenido". **Tiza suave** (tiza-suave, 7.3:1 sobre
  pizarrón): ítems de navegación en reposo, texto secundario del reloj, borde punteado del logo
  vacío.

### Tertiary (estados)
- **Verde "En el colegio"** (verde): estado presente, tramo de La jornada, tipo "Entrada",
  comando confirmado, alertas OK (con verde-fondo y verde-borde).
- **Pizarra "Se retiró"** (pizarra-estado): estado retirado, su tramo cerrado y tipo "Salida".
- **Ámbar "Sin marcar"** (ambar, 4.7:1 sobre blanco): sin marcación, comando pendiente, avisos
  (con ambar-fondo y ambar-borde), barra de "el panel no responde".
- **Rojo de peligro** (rojo): errores, campo inválido y el estado hover/foco de las acciones
  destructivas (con rojo-fondo, rojo-borde y rojo-presionado).
- **Puntos del reloj** (reloj-conectado, reloj-sin-contacto, reloj-nunca): versiones claras del
  verde, el ámbar y un gris verdoso, porque viven sobre el pizarrón; siempre junto al texto
  "Reloj conectado / sin contacto / Todavía no se conectó ningún reloj".

### Neutral
- **Blanco frío** (fondo): fondo de la página de trabajo.
- **Superficie** (superficie): planillas, formularios en línea, chips, campos y botones.
- **Superficie 2** (superficie-2): encabezados de planilla, grupo de segmentos, hover de botón,
  campo deshabilitado. **Superficie presionada** y **fila hover** (superficie-presionada,
  fila-hover): presión de botón y hover de fila.
- **Bordes** (borde, borde-fuerte): borde de tarjetas y separadores de fila; regla de La jornada,
  segmento elegido y alertas neutras.
- **Borde de control** (borde-control, 3.4:1 sobre blanco): contorno de campos y botones;
  más oscuro al pasar el mouse (borde-control-hover).
- **Texto** (texto) y **Suave** (suave, 6.5:1 sobre blanco): texto principal y secundario
  (PIN bajo el nombre, encabezados, ayudas, pies). **Placeholder** (placeholder, 4.8:1).

### Named Rules
**The Tinta Rule.** El azul de birome significa "esto se toca" (o "ahora"). No se usa como
decoración, fondo de sección ni color de estado de asistencia.

**The Texto Más Color Rule.** Ningún estado se comunica solo con color: el chip lleva punto y
palabra, el reloj lleva punto y frase, la repetida además se marca con borde punteado y cursiva.

**The Pizarrón Es Marco Rule.** El verde pizarrón pertenece a la barra, al ícono y a la fila de
títulos del Excel. Dentro del área de trabajo no aparecen fondos oscuros.

## Typography

**Display Font:** ninguna (el sistema no tiene rol display).
**Body Font:** Segoe UI Variable Text (con Segoe UI Variable, Segoe UI, system-ui, -apple-system,
Roboto, Helvetica Neue, Arial, sans-serif).

**Character:** una sola familia del sistema, sin fuentes externas (corre sin internet). La
jerarquía sale de tamaño y peso en una escala 1.125, con pesos intermedios (550, 650) que la
fuente variable de Windows resuelve con finura. `font-variant-numeric: tabular-nums` en todo el
documento.

### Hierarchy
- **Headline** (700, 1.602rem, 1.2; 1.424rem a 900 px o menos): el título de la vista; en Hoy, la
  fecha larga ("Martes 13 de octubre").
- **Hora** (600, 1.266rem; 1.125rem a 520 px o menos): la hora actual a la derecha del título, en
  suave, con el ícono de reloj.
- **Title** (650, 1.125rem, 1.2): títulos de formularios en línea ("Agregar empleado", "Datos del
  colegio") y del estado vacío grande.
- **Fila** (600, 1rem, 1.25): nombre de la persona en Hoy, horas de entrada/salida/total, nombre
  del colegio en la barra (650) y "Última marcación".
- **Body** (400, 0.889rem, 1.5): base del documento, botones (600), campos, celdas de planilla.
  Textos de ayuda y alertas limitados a 75ch.
- **Label** (600-650, 0.79rem): etiquetas de campo, encabezados de planilla, chips, PIN bajo el
  nombre, horas de la escala (500), pies "Actualizado…", estado del reloj.

### Named Rules
**The Una Familia Rule.** Una sola familia, la del sistema. La jerarquía se arma con la escala
1.125 y el peso; no se agrega una segunda fuente ni se descarga ninguna.

**The Número Tabular Rule.** Toda hora, cantidad y PIN se compone con cifras tabulares para que
las columnas queden alineadas al dígito.

## Layout

Contenedor centrado de 1360 px como máximo, con gutter de 32 px (24 px a 1100 px o menos, 16 px a
900 px o menos). La barra superior mide 68 px de alto y comparte el mismo contenedor. El área de
trabajo arranca 28 px debajo de la barra (20 px en pantallas angostas) y deja 56 px al pie.

Ritmo: fila de título (título, "Última marcación", hora) con 20 px debajo; barra de filtros con
huecos de 12 x 16 px y 16 px debajo; planilla; pie en label suave a 12 px. Los formularios de alta
y configuración van en línea, arriba de la planilla, nunca en un modal; Configuración limita su
tarjeta a 760 px.

Densidad de planilla: encabezados de 44 px (58 px en Hoy, porque alojan la escala de la jornada),
filas de 46 px (48 px en Hoy), celdas con 14 px de relleno horizontal. Hoy usa `table-layout:
fixed`: Nombre 23 %, Estado 150 px, Entrada y Salida 84 px, Horas 108 px y La jornada se queda con
el resto. El encabezado de Hoy es pegajoso.

Responsive:
- **1100 px o menos:** gutter de 24 px; Nombre 26 %, Estado 140 px.
- **900 px o menos:** controles de 44 px (objetivo táctil). La barra se parte: logo + nombre y
  reloj arriba, navegación a todo el ancho abajo con scroll horizontal y subrayado de 3 px. Los
  segmentos pasan a una grilla de 2 x 2 y el buscador a todo el ancho. Las filas de Hoy se apilan
  (nombre / estado; entrada, salida, horas con su etiqueta; la franja a todo el ancho de 36 px).
  Marcaciones también se apila (nombre y tipo arriba, fecha, hora y PIN, verificación y SN).
- **520 px o menos:** la navegación pierde los íconos; el estado del reloj pasa a dos renglones,
  siempre con texto.

## Elevation & Depth

Sistema plano. No hay ninguna sombra proyectada: la profundidad se arma con tono (fondo blanco
frío, superficies blancas, encabezados en superficie-2) y bordes de 1 px. Los únicos `box-shadow`
son indicadores insertos: el subrayado tiza del ítem de navegación actual (`inset 0 -2px 0`, o
`-3px` en móvil). Los ticks de La jornada llevan un halo de 1.5 px del color de la superficie
(`outline`) para despegarse del tramo, no una sombra.

### Named Rules
**The Plano Por Defecto Rule.** Nada flota. Una tarjeta, una planilla o un aviso se distinguen por
borde y tono, nunca por sombra. El hover cambia el fondo, no la altura.

## Shapes

Esquinas apenas redondeadas y consistentes: 8 px (md) en botones, campos, ítems de navegación,
alertas y vistas previas; 12 px (lg) en los contenedores grandes (planillas, formularios en línea,
estados vacíos). El control segmentado anida 10 px por fuera y 7 px por dentro. Los chips de estado
son píldoras (13 px sobre 26 px de alto). Lo pequeño baja a 6 px (botón de borrar búsqueda, botón
de archivo, resaltado del dato entintado) y 4 px (número del segmento). El logo vive en un disco
(50 %) de 44 px (40 px en móvil) con 3 px de tiza alrededor; sin logo, el disco es un círculo
punteado en tiza suave. Bordes siempre de 1 px salvo el disco vacío (1.5 px punteado).

Los tramos de La jornada son barras de 10 px con 3 px de radio; si el tramo sigue abierto, el
extremo derecho queda recto. Si la jornada excede la escala de 07:00 a 19:00, el extremo recortado
se dibuja en punta de flecha (recorte de 7 px).

## Components

### Buttons
Sobrios y táctiles: blancos con contorno, la tinta reservada para la acción principal.
- **Shape:** esquinas suaves (8 px), 40 px de alto (44 px a 900 px o menos), relleno de 0 16px,
  label de 600 y ícono de 20 px con 8 px de separación.
- **Default:** superficie con borde-control; hover a superficie-2 con borde-control-hover; presión
  a superficie-presionada y baja 1 px.
- **Primario:** tinta con texto blanco ("Exportar a Excel", "Agregar empleado", "Guardar"). Hover
  tinta-hover, presión tinta-activa. Uno por vista como máximo.
- **Fantasma:** sin fondo ni borde, texto en tinta; hover con tinta-12 ("Ver todo").
- **Peligro:** neutro en reposo (igual que el default); el rojo aparece solo con hover o foco
  (rojo-fondo, borde y texto rojo). Siempre confirma antes de actuar.
- **Chico:** 32 px de alto, 0 10px, label 0.79rem, ícono de 16 px (acciones por fila).
- **Cargando:** oculta el ícono y muestra un aro de 14 px que gira (0.8 s lineal); el botón de
  Excel lo usa 2.5 s al descargar.
- **Deshabilitado:** opacidad 0.5, cursor no permitido.
- **Foco:** contorno de 2 px en tinta con separación de 2 px (en toda la interfaz).

### Chips (estado)
- **Style:** píldora blanca de 26 px, label de 650, borde del color del texto al 30 % mezclado con
  blanco; punto de 8 px + palabra. Colores: verde (En el colegio), pizarra-estado (Se retiró),
  ambar (Sin marcar).
- **Comandos al reloj:** misma píldora, 24 px de línea, primera letra en mayúscula: pendiente en
  ámbar, enviado en tinta, ok en verde, error en rojo.
- **Tipo de marcación:** píldora de 24 px. Entrada verde, Salida pizarra, Intermedia en texto,
  Repetida en suave con borde punteado y peso 550 (y su fila entera en suave).

### Control segmentado (resumen y filtro de Hoy)
El resumen del día es a la vez el filtro: "Todos 42 · En el colegio 30 · Se retiraron 4 · Sin
marcar 8".
- **Style:** grupo en superficie-2 con borde y 3 px de relleno; segmentos de 32 px (40 px en
  móvil), texto suave, punto de color de estado y el número en texto a 700.
- **State:** hover con blanco al 70 %; elegido con superficie blanca, borde-fuerte y texto. El
  elegido se refleja en `aria-pressed` y en la URL.

### Cards / Containers
- **Corner Style:** 12 px.
- **Background:** superficie sobre fondo.
- **Shadow Strategy:** ninguna (ver Elevation & Depth).
- **Border:** 1 px en borde.
- **Internal Padding:** 20px 24px (16 px en móvil) en formularios en línea; estados vacíos con
  36-56 px vertical, ícono de 32 px, título en Title y texto a 52ch.

### Inputs / Fields
- **Style:** 40 px de alto, 0 12px, borde-control de 1 px, 8 px de radio, superficie. Etiqueta
  encima en label suave (en Configuración, 0.889rem a 650 en texto).
- **Hover:** borde-control-hover. **Focus:** borde en tinta + contorno de 2 px en tinta sin
  separación.
- **Select:** sin apariencia nativa, chevron propio de 18 px en suave.
- **Buscador:** ícono de lupa dentro a la izquierda, botón de borrar de 32 px a la derecha;
  Escape limpia.
- **Error / Disabled:** `:user-invalid` pasa el borde y el foco a rojo; deshabilitado en
  superficie-2 con texto suave.

### Alertas y avisos
- Caja de 8 px de radio, 12px 14px, ícono de 20 px, máximo 75ch. Variantes OK (verde-fondo,
  verde-borde), aviso (ambar-fondo, ambar-borde) y error (rojo-fondo, rojo-borde); el ícono lleva
  el color fuerte, el texto queda en texto.
- **Panel sin respuesta:** franja de ancho completo bajo la barra, ambar-fondo con borde inferior
  ambar-borde.

### Navigation
- **Barra:** pizarrón de 68 px con logo + nombre del colegio (2 renglones máximo), navegación e
  indicador del reloj a la derecha (punto de 8 px + texto, refresco cada 5 s).
- **Ítems:** 40 px, 0 14px, tiza-suave a 550 con ícono; hover con tiza al 10 %, presión al 18 %;
  actual con tiza al 16 %, texto blanco a 650 y subrayado inserto de 2 px en tiza.
- **Móvil:** ver Layout (fila propia con scroll horizontal, sin radio, subrayado de 3 px).
- **Sin nombre ni logo:** el enlace "Cargá el nombre y el logo del colegio" en tiza, subrayado; el
  disco vacío punteado lleva a Configuración. Nunca un nombre o logo inventado.

### Íconos
Sprite propio (`/static/iconos.svg`), 24 x 24, trazo de 1.5 px, puntas y uniones redondas, sin
relleno, en `currentColor`. Se muestran a 20 px (16 px en botones chicos, 32 px en estados vacíos).
Siempre decorativos (`aria-hidden`) junto a un texto.

### La jornada (firma)
Cada fila de Hoy tiene una franja horizontal sobre la escala de 07:00 a 19:00.
- **Escala:** en el encabezado, el título "La jornada" y las horas impares (07, 09 … 19) en label
  suave a 500. Debajo de cada fila, una regla de borde-fuerte con una marca por hora (12 tramos).
- **Tramo:** barra de 10 px y 3 px de radio, de la entrada a la salida, en verde; en pizarra-estado
  si la persona se retiró. Ancho mínimo de 6 px. Si sigue en el colegio, el tramo termina
  exactamente en "ahora" con el extremo recto y sus últimos 10 px "respiran" (se aclaran hasta 70 %
  y vuelven, 2.4 s, ease-in-out, en bucle).
- **Ticks:** cada marcación intermedia es una raya de 2 x 20 px en texto con halo de superficie.
- **Ahora:** una línea vertical de 1.5 px en tinta cruza todas las filas; en el encabezado nace de
  un triángulo de tinta bajo las horas. Fuera del horario de la escala, no se dibuja.
- **Recorte:** si la jornada empieza antes de las 07:00 o termina después de las 19:00, el extremo
  recortado termina en punta.
- La franja es decorativa para lectores de pantalla (`aria-hidden`): la misma información está en
  las columnas Estado, Entrada, Salida y Horas.

### Entintado (gesto vivo)
Cuando el refresco (cada 5 s) trae una marcación nueva, lo que cambió se "entinta": aparece con un
relleno de tinta al 28 % que se desvanece a transparente en 1.2 s con ease-out exponencial
(`cubic-bezier(0.16, 1, 0.3, 1)`). Se entinta la celda de hora de esa fila (entrada o salida, la
que cambió), el dato de "Última marcación" junto al título y el número del segmento cuyo conteo
cambió. Con `prefers-reduced-motion` no hay entintado ni respiración: solo el estado final.

### Excel exportado
El documento del colegio en papel. Hojas: "Resumen por día" (primera y activa), "Detalle" e
"Info".
- **Encabezado de documento** (filas 1 a 3): logo PNG/JPG (máx. 150 x 52 px, columnas A-B; el SVG no
  se inserta), nombre del colegio (16 pt, negrita, verde pizarrón), "Asistencia del personal"
  (12 pt, negrita, suave) y período · empleado · fecha de emisión (10 pt, suave). Fila 4 de aire.
- **Títulos** (fila 5, 24 pt de alto): fondo verde pizarrón, texto blanco en negrita; columnas de
  fecha, hora, PIN y cantidades centradas, el resto a la izquierda con sangría 1. Paneles
  congelados y autofiltro.
- **Filas:** cebra muy suave en filas alternas, línea inferior fina, sin cuadrícula. El Tipo lleva
  su color de estado (Repetida en cursiva).
- **Observación:** en ámbar (fondo y texto) solo si es una alerta; "Sin salida todavía" (hoy, a media
  jornada) va en suave y cursiva.
- **Total:** negrita con línea superior media en verde pizarrón; debajo, las notas de cálculo en
  cursiva suave.
- **Impresión:** A4 horizontal, 1 página de ancho, títulos repetidos, centrado, pie "Página N de M"
  en 9 pt suave.
- Paleta propia del Excel (ver el sidecar): coincide en verde y estados con el panel, pero usa
  suave, ámbar, cebra y borde ajustados al papel.

## Do's and Don'ts

### Do:
- **Do** usar la tinta (#2747b8) solo para acciones, enlaces, foco, selección y "ahora".
- **Do** acompañar cada color de estado con su palabra (punto + "En el colegio", "Se retiró",
  "Sin marcar"; "Reloj conectado · hace 3 s").
- **Do** componer horas, cantidades y PIN con cifras tabulares y alinearlos en columna.
- **Do** mantener la densidad de planilla: filas de 46-48 px, celdas con 14 px de relleno.
- **Do** separar superficies con borde de 1 px y tono; radios de 8 px en controles y 12 px en
  contenedores.
- **Do** dibujar íconos nuevos en el sprite propio: 24 x 24, trazo de 1.5 px, redondeados, sin
  relleno.
- **Do** dar a cada animación su alternativa de movimiento reducido (estado final sin animar).
- **Do** usar ease-out exponencial (`cubic-bezier(0.16, 1, 0.3, 1)`) para lo que aparece y 0.15 s
  para cambios de color de hover.
- **Do** dejar las acciones destructivas neutras en reposo y pedir confirmación.
- **Do** mostrar el estado vacío "Cargá el nombre y el logo del colegio" cuando falten.

### Don't:
- **Don't** armar un dashboard de tarjetas con números grandes ni una tabla gris con un acento
  azul: la jornada se lee como franja por persona.
- **Don't** usar sombras proyectadas; la única sombra permitida es el subrayado inserto del ítem
  de navegación actual.
- **Don't** usar fondos oscuros dentro del área de trabajo: el pizarrón es solo el marco.
- **Don't** cargar fuentes, íconos ni scripts desde un CDN; todo es local.
- **Don't** poner formularios en modales: el alta y la edición van en línea.
- **Don't** inventar nombre ni logo del colegio.
- **Don't** pintar en rojo una acción destructiva en reposo.
