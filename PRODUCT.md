# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Secretaría / administración del colegio** (uso diario): controla quién llegó, da de alta y de
  baja al personal en el reloj y exporta el Excel de asistencia (típicamente a fin de mes).
- **Dirección** (consulta): mira de un vistazo quién vino y quién falta hoy, sin operar.
- Personal registrado: entre 30 y 80 empleados, docentes y no docentes.

## Product Purpose

Control de asistencia del personal de un colegio con un reloj biométrico ZKTeco (reconocimiento
facial). Reemplaza a ZKBio Time con algo simple y gratuito: el reloj manda cada marcación en tiempo
real a una PC del colegio y el panel muestra la asistencia del día, el historial y los empleados.
Éxito: en segundos se sabe quién está, quién se retiró y quién no marcó; el Excel del mes sale
listo para entregar.

## Positioning

Corre entero en una PC del colegio, sin nube, sin licencias y sin internet. Un solo `.exe`.

## Operating Context

- PC de escritorio Windows 10/11 en la secretaría; el panel se abre en el navegador de esa PC
  (`http://localhost:8081`), solo desde ahí.
- Horario diurno únicamente (no hay turnos nocturnos). Por ahora se marca solo entrada y salida,
  sin almuerzo ni horarios cargados.
- La primera marcación del día es la entrada y la última es la salida.
- El registro facial se hace en el propio reloj; el panel da de alta, modifica y da de baja.

## Capabilities and Constraints

- Panel en español (Argentina). Jinja2 + HTMX, sin CDN, sin frameworks JS.
- Vistas: hoy (presentes / se retiraron / sin marcar), marcaciones con filtros, empleados (ABM con
  estado de cada comando enviado al reloj), exportación a Excel (detalle + resumen por día).
- Administradores del reloj protegidos: no se editan ni se dan de baja desde el panel.
- No hay turnos, tardanzas ni horas extra (undecided: posible etapa futura).

## Brand Commitments

- Lleva el nombre y el logo del colegio en el panel y en el Excel (confirmado). El nombre y el
  archivo del logo todavía no se entregaron: deben poder cargarse desde el panel, sin tocar código.
  No inventar nombre ni logo.

## Evidence on Hand

- Datos reales: un empleado administrador (PIN 1) y marcaciones de prueba del 2026-10-13.
- No hay logo, fotos ni nombre del colegio todavía.

## Product Principles

1. Lo de hoy primero: la pregunta diaria es "¿quién vino?", la respuesta tiene que estar al abrir.
2. Nada se pierde ni se duplica; el estado de cada operación con el reloj siempre está a la vista.
3. Lenguaje de escuela, no de software: entrada, salida, personal, libro de asistencia.
4. Simple de operar para cualquier persona de la secretaría, sin capacitación.

## Accessibility & Inclusion

- Lectura cómoda en monitores de oficina comunes; contraste AA mínimo; operable con teclado.
