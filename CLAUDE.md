# mini-asistencia

Sistema simple y gratuito de control de asistencia para relojes biométricos ZKTeco que usan
el protocolo ADMS/PUSH (HTTP, rutas `/iclock/...`). Reemplaza a ZKBio Time.

- Repo: `https://github.com/oran-soluciones/mini-asistencia.git` (rama `main`; acceso por HTTPS
  autenticado con GitHub CLI `gh`, sin SSH)
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

## Entorno Python
- Siempre trabajar dentro de un entorno virtual `.venv` en la raíz del proyecto
  (`py -3.12 -m venv .venv`). Nunca instalar paquetes en el Python global.
- Ejecutar todo con el Python del venv: `.venv\Scripts\python.exe` en Windows,
  `.venv/bin/python` en Linux (o activar con `.venv\Scripts\Activate.ps1`).
- Dependencias fijadas en `requirements.txt`; `.venv/` va en `.gitignore`.
- Tests: `.venv\Scripts\python.exe -m pip install -r requirements-dev.txt` y luego
  `.venv\Scripts\python.exe -m pytest -q` (usan `tests/fixtures/`, base y samples temporales).

## Reglas
- Priorizar simplicidad: pocos archivos, pocas dependencias, nada de sobre-ingeniería.
- Indentación: 2 espacios en todos los archivos (Python incluido), nunca tabs. Fin de línea LF.
  Lo fijan `.editorconfig`, `.gitattributes` y `.vscode/settings.json`.
- Loguear SIEMPRE el request crudo que manda el reloj (método, URL, query, headers, body)
  y guardar ejemplos reales en `samples/`. `samples/` es local y NO se sube a Git (tiene
  contraseñas, SN, MAC). Los tests usan copias anonimizadas en `tests/fixtures/`.
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
├─ samples/          # requests reales capturados del reloj (local, fuera de Git)
├─ tests/            # pytest; tests/fixtures/ = samples anonimizados
└─ .github/workflows/build-windows.yml
```

## Etapas
0. **Preparación**: repo (HTTPS), venv con Python 3.12, `.gitignore`.
1. **Servidor espía**: ruta comodín `/iclock/{path}` que loguea todo crudo, guarda cada request
   en `samples/` y responde lo mínimo para que el reloj siga hablando. Objetivo: descubrir
   qué rutas y formato usa realmente este firmware.
2. **Marcaciones**: parsear ATTLOG según los samples reales, guardar en SQLite sin duplicados,
   tests con fixtures anonimizados sacados de los samples.
3. **Panel de lectura**: lista de marcaciones (filtros por fecha/empleado) y empleados.
4. **ABM de empleados**: cola de comandos en SQLite, entrega por `/iclock/getrequest`,
   confirmación por `/iclock/devicecmd`, estado visible en el panel.
5. **Reportes Excel**: marcaciones por rango de fechas/empleado.
6. **Empaquetado**: PyInstaller + pystray + apertura del navegador; workflow de GitHub Actions
   que genera el `.exe` en `windows-latest`.
7. **Prueba en Windows real**: firewall, IP fija, arranque, reinicio de PC.

## Protocolo verificado (etapa 1, 2026-10-13)
Variante PUSH clásica (`PushVersion=Ver 2.0.33S-20211012`, user-agent `iClock Proxy/1.09`).
Sin `/iclock/registry` ni `/iclock/push`. Todos los bodies son `text/plain`.
- `GET /iclock/cdata?SN=..&options=all&language=101&pushver=2.4.1&PushOptionsFlag=1`: saludo;
  acepta la respuesta `GET OPTION FROM: <SN>` + `clave=valor` por línea (ver `iclock.py`).
- `POST /iclock/cdata?SN=..&table=options`: info del equipo en una línea `clave=valor,...`
  (algunas claves con `~`).
- `POST /iclock/cdata?SN=..&table=ATTLOG&Stamp=..`: una marcación por línea, separada por tab:
  `PIN  YYYY-MM-DD HH:MM:SS  estado  verificación  0 0 0 0 0 0` (con tab final). Llegan en
  lote las guardadas y luego en tiempo real, una por POST. `15` en verificación = cara
  (deducido, no verificado).
- `POST /iclock/cdata?SN=..&table=OPERLOG&OpStamp=..`: líneas `OPLOG ...` (tab) y también
  `USER PIN=..<tab>Name=..<tab>Pri=..<tab>Passwd=..<tab>Card=..<tab>Grp=..<tab>TZ=..<tab>Verify=..`.
- `GET /iclock/getrequest?SN=..` cada 2-5 s (la primera trae `INFO=fw,usuarios,?,marcaciones,ip,...`).
  Respondemos `OK` = sin comandos.
- `/iclock/devicecmd`: todavía no visto (aparece cuando se le manden comandos).
- El reloj tenía la hora ~4 min 20 s adelantada respecto de la PC.

## Riesgos y dudas a verificar
- Codificación de nombres (tildes, ñ) que acepta el reloj.
- Si `DATA UPDATE USERINFO` sobre un PIN existente conserva la cara registrada.
- Firewall de Windows (regla de entrada en el puerto; red marcada como "Pública" bloquea).
- IP fija de la PC (reserva DHCP en el router), porque el reloj apunta a una IP.
- No correr al mismo tiempo que ZKBio Time (conflicto de puerto).
- Hora del reloj vs. hora de la PC (zona horaria, sincronización).
- Seguridad: `/iclock` debe escuchar en la red; el panel conviene limitarlo a localhost.
- `.exe` sin firmar: aviso de SmartScreen o falsos positivos del antivirus.
