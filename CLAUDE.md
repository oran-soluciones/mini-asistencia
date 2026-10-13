# mini-asistencia

Sistema simple y gratuito de control de asistencia para relojes biométricos ZKTeco que usan
el protocolo ADMS/PUSH (HTTP, rutas `/iclock/...`). Reemplaza a ZKBio Time.

- Repo: `git@github.com:oran-soluciones/mini-asistencia.git` (rama `main`)
- Carpeta local: `D:\Programas\oran-soluciones\mini-asistencia`

## Contexto del equipo
- ZKTeco Horus TL2, solo reconocimiento facial, conexión Wi-Fi.
- Firmware ZMM510-NF-Ver 1.0.21. En "Config SVR de nube" solo ofrece modo ADMS (no BEST),
  por eso no sirve ZKBio Zlink.
- El reloj se configura con la IP y el puerto de la PC donde corre este programa.
- El producto final corre en Windows 10 y 11.

## Objetivo de la versión mini
1. Recibir marcaciones en tiempo real (ATTLOG) y guardarlas.
2. Panel web local para ver marcaciones y empleados.
3. ABM de empleados desde el panel, enviando comandos al reloj
   (`DATA UPDATE USERINFO` / `DATA DELETE USERINFO` vía `/iclock/getrequest`).
   El registro facial se hace en el propio reloj.
4. Exportar reportes de asistencia a Excel.
5. Un único `.exe` (PyInstaller): doble clic levanta servidor + panel, abre el navegador
   y pone un ícono en la bandeja. Build de Windows vía GitHub Actions.

## Stack
Python 3.12, FastAPI + Uvicorn, SQLite (módulo `sqlite3` estándar, sin ORM),
Jinja2 + HTMX para el panel, openpyxl, PyInstaller, pystray.
Usar `pathlib` para todas las rutas (compatibilidad Windows/Linux).

## Reglas
- Priorizar simplicidad: pocos archivos, pocas dependencias, nada de sobre-ingeniería.
- Loguear SIEMPRE el request crudo que manda el reloj (método, URL, query, headers, body)
  y guardar ejemplos reales en `samples/` para usarlos en tests.
- No asumir campos del protocolo sin verificarlos contra lo que realmente manda el reloj.
  Si algo no está en `samples/`, se marca como "no verificado".
- Las marcaciones nunca se pierden ni se duplican: clave única (SN, PIN, fecha-hora).
- Los datos del usuario (SQLite, logs) van en una carpeta de datos del usuario
  (en Windows `%LOCALAPPDATA%\mini-asistencia`), nunca al lado del `.exe`.
- Esperar aprobación del usuario antes de empezar cada etapa.

## Estructura prevista
```
mini-asistencia/
├─ CLAUDE.md
├─ README.md
├─ requirements.txt
├─ .gitignore
├─ app/
│  ├─ main.py        # punto de entrada: Uvicorn + bandeja (pystray) + abrir navegador
│  ├─ config.py      # puerto, carpeta de datos, rutas (pathlib)
│  ├─ iclock.py      # rutas /iclock/* (protocolo ADMS) + log crudo
│  ├─ db.py          # esquema SQLite y consultas
│  ├─ panel.py       # rutas del panel web (HTML/HTMX)
│  ├─ reports.py     # exportación a Excel (openpyxl)
│  ├─ templates/     # Jinja2: base, marcaciones, empleados, parciales HTMX
│  └─ static/        # htmx.min.js (local, sin CDN), style.css, ícono
├─ samples/          # requests reales capturados del reloj
├─ tests/            # pytest usando samples/
└─ .github/workflows/build-windows.yml
```

## Etapas
0. **Preparación**: repo, SSH, venv con Python 3.12, `.gitignore`.
1. **Servidor espía**: ruta comodín `/iclock/{path}` que loguea todo crudo, guarda cada request
   en `samples/` y responde lo mínimo para que el reloj siga hablando. Objetivo: descubrir
   qué rutas y formato usa realmente este firmware.
2. **Marcaciones**: parsear ATTLOG según los samples reales, guardar en SQLite sin duplicados,
   tests con samples.
3. **Panel de lectura**: lista de marcaciones (filtros por fecha/empleado) y empleados.
4. **ABM de empleados**: cola de comandos en SQLite, entrega por `/iclock/getrequest`,
   confirmación por `/iclock/devicecmd`, estado visible en el panel.
5. **Reportes Excel**: marcaciones por rango de fechas/empleado.
6. **Empaquetado**: PyInstaller + pystray + apertura del navegador; workflow de GitHub Actions
   que genera el `.exe` en `windows-latest`.
7. **Prueba en Windows real**: firewall, IP fija, arranque, reinicio de PC.

## Riesgos y dudas a verificar
- Variante del protocolo según firmware (clásico `cdata`/`getrequest` vs. versiones nuevas con
  `/iclock/registry` y `/iclock/push`). Lo resuelve la etapa 1.
- Codificación de nombres (tildes, ñ) que acepta el reloj.
- Si `DATA UPDATE USERINFO` sobre un PIN existente conserva la cara registrada.
- Firewall de Windows (regla de entrada en el puerto; red marcada como "Pública" bloquea).
- IP fija de la PC (reserva DHCP en el router), porque el reloj apunta a una IP.
- No correr al mismo tiempo que ZKBio Time (conflicto de puerto).
- Hora del reloj vs. hora de la PC (zona horaria, sincronización).
- Seguridad: `/iclock` debe escuchar en la red; el panel conviene limitarlo a localhost.
- `.exe` sin firmar: aviso de SmartScreen o falsos positivos del antivirus.
