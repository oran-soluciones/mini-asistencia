# mini-asistencia

Control de asistencia simple y gratuito para relojes biométricos **ZKTeco** que usan el protocolo
**ADMS/PUSH** (HTTP, rutas `/iclock/...`). Reemplaza a ZKBio Time para un colegio: el reloj manda
cada marcación en tiempo real a una PC y un panel web local muestra quién llegó, quién se retiró y
quién no marcó, permite dar de alta y de baja al personal en el reloj y exporta la asistencia a
Excel.

Corre entero en una PC con Windows 10 u 11: sin nube, sin licencias y sin internet. Es un solo
`.exe`.

---

## Contenido

- [Qué hace](#qué-hace)
- [Instalación en la PC del colegio](#instalación-en-la-pc-del-colegio)
- [Conectar el reloj](#conectar-el-reloj)
- [Uso del panel](#uso-del-panel)
- [Cómo se calcula la jornada](#cómo-se-calcula-la-jornada)
- [El reporte de Excel](#el-reporte-de-excel)
- [Datos, respaldo y actualización](#datos-respaldo-y-actualización)
- [Solución de problemas](#solución-de-problemas)
- [Desarrollo](#desarrollo)
- [Generar el .exe](#generar-el-exe)
- [Protocolo del reloj](#protocolo-del-reloj)
- [Limitaciones conocidas](#limitaciones-conocidas)

---

## Qué hace

- **Recibe las marcaciones en tiempo real** del reloj y las guarda sin perder ni duplicar
  ninguna (clave única: reloj, empleado, fecha y hora).
- **Hoy**: la asistencia de un día con el estado de cada persona (En el colegio, Se retiró, Sin
  marcar), sus horas y una línea de tiempo de 07 a 19 h. Se puede elegir cualquier día anterior.
- **Marcaciones**: el historial con filtros por fecha y empleado. Cada marcación muestra si es
  Entrada, Salida o Repetida, y se puede **anular** (por ejemplo, si alguien marcó dos veces).
- **Empleados**: alta, modificación y baja desde el panel. Los cambios se mandan al reloj y se ve
  si los confirmó. La cara se registra en el propio reloj.
- **Exportar a Excel**: resumen por día, línea de tiempo, detalle de marcaciones e información
  del reporte, listo para imprimir.
- **Configuración**: nombre y logo del colegio (salen en el panel y en el Excel) y una guía para
  conectar el reloj con la IP de la PC y los comandos necesarios.
- **Ícono en la bandeja** de Windows, con opción de arrancar solo al prender la PC.

El panel **solo se abre desde la misma PC** (`http://localhost:8081/`). Desde otras computadoras
de la red responde "403": así nadie más puede ver ni cambiar datos. El reloj sí llega por la red
a las rutas `/iclock/...`.

---

## Instalación en la PC del colegio

**Requisitos**: Windows 10 u 11, la PC y el reloj en la misma red (Wi-Fi o cable), y el puerto
`8081` libre (no puede estar abierto ZKBio Time al mismo tiempo).

1. **Descargá `mini-asistencia.exe`** desde la sección *Releases* del repositorio o desde los
   *artifacts* de GitHub Actions (ver [Generar el .exe](#generar-el-exe)).
2. **Dejalo en una carpeta fija**, por ejemplo `C:\mini-asistencia\mini-asistencia.exe`. Si
   después lo movés, hay que volver a activar "Iniciar con Windows".
3. **Abrilo con doble clic.**
   - Si aparece *"Windows protegió su PC"* (el `.exe` no está firmado): **Más información →
     Ejecutar de todas formas**.
   - Si el firewall pregunta por el acceso a la red: marcá **Redes privadas → Permitir**.
4. Se abre el panel en el navegador y aparece el ícono del reloj en la bandeja, al lado de la hora
   de Windows (si no se ve, puede estar detrás de la flechita **^**).
5. **Clic derecho en el ícono → Iniciar con Windows.** Desde ahí arranca solo cada vez que se
   prende la PC y alguien inicia sesión, sin abrir el navegador.

### El ícono de la bandeja

| Opción | Qué hace |
|---|---|
| **Abrir panel** (o doble clic) | Abre `http://localhost:8081/` en el navegador. |
| **Iniciar con Windows** | Arranca solo al iniciar sesión en Windows (se guarda en el registro del usuario). |
| **Carpeta de datos** | Abre la carpeta donde están la base, el logo y los logs. |
| **Salir** | Cierra el programa. No se pierde nada: el reloj guarda las marcaciones y las manda al volver a abrir. |

Hacer doble clic en el `.exe` con el programa ya abierto no abre otra copia: solo muestra el panel.

---

## Conectar el reloj

Todo esto también está explicado en el panel, en **Configuración → Conectar el reloj**, con la IP
de la PC ya escrita y botones para copiar los comandos.

### 1. En la PC (una sola vez)

Abrí **PowerShell como administrador** (clic derecho en Inicio → Terminal (administrador)):

```powershell
# Abrir el puerto en el firewall de Windows
netsh advfirewall firewall add rule name="mini-asistencia 8081" dir=in action=allow protocol=TCP localport=8081

# Marcar la red como Privada (en una red Pública Windows bloquea las conexiones entrantes)
Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private

# Comprobar que el programa está escuchando (tiene que aparecer 0.0.0.0:8081 ... LISTENING)
netstat -ano | findstr :8081

# Ver la IP de la PC ("Dirección IPv4" del adaptador conectado a la red del reloj)
ipconfig
```

**IP fija**: el reloj apunta a una IP. Pedí en el router una *reserva DHCP* para la PC; si la IP
cambia, hay que volver a cargarla en el reloj.

### 2. En el reloj

1. Entrá al menú con un usuario administrador → **Comunicación** → **Config SVR de nube**
   (*Cloud Server Setting*).
2. Modo del servidor: **ADMS**. Nombre de dominio: **desactivado**.
3. Dirección del servidor: **la IP de la PC**. Puerto: **8081**. Proxy: desactivado.
4. Guardá. En unos segundos la barra del panel dice **Reloj conectado** (si no, reiniciá el reloj).

Revisá también que la **fecha y hora del reloj** coincidan con las de la PC.

---

## Uso del panel

### Hoy

- Arriba: la fecha, la última marcación recibida y la hora de la PC.
- **Elegir el día**: con **‹** y **›** se pasa al día anterior o siguiente, y con **📅 Elegir
  día** se abre un calendario. En un día anterior aparece **Volver a hoy**.
- Filtros por estado (Todos, En el colegio, Se retiraron, Sin marcar) y buscador por nombre o PIN.
- Por persona: estado, primera entrada, última salida, horas y la **línea de tiempo** (un tramo
  por cada par entrada-salida; si salió y volvió se ve el hueco).
- Se actualiza sola cada 5 segundos. Cuando llega una marcación, la hora se resalta en azul.
- En un día anterior nadie "sigue en el colegio": quien no marcó la salida aparece como
  **Sin salida**, en rojo.

### Marcaciones

- Filtros desde/hasta y por empleado (sin filtros muestra el día de hoy; **Ver todo** quita las
  fechas).
- Cada fila dice si es **Entrada**, **Salida**, **Repetida** o **Anulada**.
- **Anular**: si alguien marcó de más (por ejemplo dos veces la entrada y entonces "nunca
  salió"), se anula esa marcación. No se borra: queda tachada, deja de contar en Hoy y en el
  Excel, y las demás del día se reacomodan solas. **Restaurar** la vuelve a contar.
- **Exportar a Excel** usa los mismos filtros.

### Empleados

- **Alta**: PIN (número de 1 a 9 dígitos, sin ceros a la izquierda), nombre (hasta 24
  caracteres) y nivel. Se crea en el panel y se manda al reloj; la cara se registra después en el
  reloj.
- **Editar** y **Dar de baja**: se mandan al reloj como comandos. La baja borra al empleado del
  reloj, con su cara.
- La columna *Último comando* muestra si el reloj lo confirmó (pendiente, enviado, confirmado o
  error). Los comandos se reintentan hasta 3 veces.
- Los **administradores** del reloj no se tocan desde el panel: se gestionan en el propio reloj.

### Configuración

- Nombre y logo del colegio (PNG, JPG o SVG, hasta 1 MB). El Excel inserta el logo solo si es PNG
  o JPG.
- **Conectar el reloj**: IP de la PC, puerto, estado del reloj, pasos y comandos.

---

## Cómo se calcula la jornada

Es la misma regla para Hoy, la columna Tipo de Marcaciones y el Excel (`app/jornada.py`):

- Las marcaciones válidas de cada día van **de a pares**: la 1.ª es entrada, la 2.ª salida, la
  3.ª entrada, la 4.ª salida, y así. **Cada día empieza de nuevo con una entrada.**
- **Horas** = suma de cada par entrada-salida. El tiempo afuera entre una salida y la siguiente
  entrada no cuenta. No contempla turnos ni horarios cargados.
- Una marcación a **menos de 2 minutos** de la anterior es **repetida** y se ignora (típico de
  marcar dos veces seguidas).
- Las **anuladas** no cuentan.
- Si la cantidad es impar, a la última entrada le falta la salida: hoy significa que sigue en el
  colegio; en un día anterior, que se olvidó de marcar la salida (no suma horas).
- No se cruza la medianoche: cada día se calcula por separado (el colegio es solo diurno).

---

## El reporte de Excel

`Exportar a Excel` genera un `.xlsx` con el nombre y el logo del colegio, el período y la fecha de
emisión, listo para imprimir en A4 horizontal:

| Hoja | Contenido |
|---|---|
| **Resumen por día** | Una fila por persona y día: Entrada 1, Salida 1, Entrada 2, Salida 2... (tantas como hagan falta), cantidad, horas trabajadas y observación (repetidas, salida faltante, anuladas). Fila de total. |
| **Línea de tiempo** | Una fila por persona y día con el horario escrito y columnas de 15 minutos pintadas: gris oscuro = estuvo en el colegio, verde = sigue (hoy), ámbar = entrada sin salida. |
| **Detalle** | Cada marcación con fecha, hora, tipo, PIN, nombre, verificación y reloj. |
| **Info** | Filtros usados, cantidad de marcaciones, fecha de emisión y las reglas del cálculo. |

---

## Datos, respaldo y actualización

Los datos **no** están dentro del `.exe` ni a su lado, sino en la carpeta del usuario:

```
%LOCALAPPDATA%\mini-asistencia\
├─ asistencia.db     marcaciones, empleados, anulaciones y comandos (SQLite)
├─ colegio.json      nombre del colegio
├─ logo.*            logo del colegio
├─ logs\             iclock.log (rotativo, hasta 10 archivos de 5 MB)
└─ samples\          requests crudos del reloj (diagnóstico)
```

- **Cerrar o reabrir** el programa no borra nada.
- **Actualizar**: Salir desde la bandeja, reemplazar el `.exe` por el nuevo (en la misma carpeta)
  y abrirlo. La base se actualiza sola si hace falta.
- **Respaldo**: copiá `asistencia.db` (con el programa cerrado) a un pendrive de vez en cuando.
- **Desinstalar**: desactivá *Iniciar con Windows*, **Salir** y borrá el `.exe`. Los datos quedan
  hasta que borres la carpeta de arriba.

---

## Solución de problemas

| Síntoma | Qué revisar |
|---|---|
| La barra dice **"Todavía no se conectó ningún reloj"** o **"Reloj sin contacto"** | IP y puerto cargados en el reloj; regla del firewall; red marcada como Privada; PC y reloj en la misma red. `netstat -ano \| findstr :8081` tiene que mostrar `LISTENING`. |
| Cartel **"El puerto 8081 lo está usando otro programa"** | Cerrá ZKBio Time (o lo que use ese puerto) y volvé a abrir mini-asistencia. |
| El panel no abre desde otra computadora | Es a propósito: el panel solo responde en la misma PC (`http://localhost:8081/`). |
| Alguien "nunca salió" porque marcó dos veces | En Marcaciones, anulá la marcación de más. |
| Las horas no coinciden con lo esperado | Revisá la hora del reloj contra la de la PC (menú Sistema → Fecha y hora del reloj). |
| Un comando de empleado quedó en "pendiente" | El reloj tiene que estar conectado; se entrega en el próximo contacto y se reintenta hasta 3 veces. |
| Windows o el antivirus bloquean el `.exe` | El `.exe` no está firmado: "Más información → Ejecutar de todas formas", o agregá una excepción en el antivirus. |
| No arranca solo al prender la PC | Activá *Iniciar con Windows* desde el ícono. Arranca al **iniciar sesión**, no antes. Si moviste el `.exe`, volvé a activarlo. |

Los detalles de cada request quedan en `%LOCALAPPDATA%\mini-asistencia\logs\iclock.log`.

---

## Desarrollo

**Stack**: Python 3.12, FastAPI + Uvicorn, SQLite (`sqlite3` estándar, sin ORM), Jinja2 + HTMX
(local, sin CDN), openpyxl, pystray y PyInstaller.

```
mini-asistencia/
├─ app/
│  ├─ main.py        # punto de entrada: servidor + bandeja (pystray) + navegador
│  ├─ config.py      # puerto, carpeta de datos, rutas (pathlib)
│  ├─ iclock.py      # rutas /iclock/* (protocolo ADMS) + log crudo y samples
│  ├─ db.py          # esquema SQLite y consultas
│  ├─ jornada.py     # la regla de la jornada (pares, repetidas, anuladas) y la vista Hoy
│  ├─ panel.py       # rutas del panel web (HTML/HTMX)
│  ├─ reports.py     # exportación a Excel (openpyxl)
│  ├─ colegio.py     # nombre y logo del colegio
│  ├─ templates/     # Jinja2
│  └─ static/        # htmx.min.js, style.css, panel.js, íconos
├─ tests/            # pytest; tests/fixtures/ = samples anonimizados
├─ samples/          # requests reales del reloj (local, NO se sube a Git)
├─ mini-asistencia.spec
└─ .github/workflows/build-windows.yml
```

### Preparar el entorno (Windows)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Siempre con el Python del `.venv`; nunca instalar paquetes en el Python global.

### Correr

```powershell
.venv\Scripts\python.exe -m app.main
```

Opciones: `--sin-navegador` (no abre el navegador) y `--sin-bandeja` (sin ícono; útil para
pruebas). Variables de entorno para probar sin tocar los datos reales:

| Variable | Para qué |
|---|---|
| `MINI_ASISTENCIA_PORT` | Puerto (por defecto `8081`). |
| `MINI_ASISTENCIA_DATA_DIR` | Carpeta de la base, el logo y los logs. |
| `MINI_ASISTENCIA_SAMPLES_DIR` | Carpeta donde se guardan los requests crudos. |

Por ejemplo, una instancia de prueba en el 8091 con una base aparte:

```powershell
$env:MINI_ASISTENCIA_PORT = "8091"; $env:MINI_ASISTENCIA_DATA_DIR = "$env:TEMP\mini-demo"
.venv\Scripts\python.exe -m app.main --sin-bandeja
```

### Tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Usan una base, samples y carpeta de datos temporales, y fixtures anonimizados en
`tests/fixtures/`: nunca tocan los datos reales.

### Convenciones

- Indentación de 2 espacios en todos los archivos (Python incluido), sin tabs; fin de línea LF
  (lo fijan `.editorconfig`, `.gitattributes` y `.vscode/settings.json`).
- Rutas siempre con `pathlib`.
- Se loguea siempre el request crudo del reloj. `samples/` tiene datos sensibles (SN, MAC,
  contraseñas) y no se sube a Git.
- No se asumen campos del protocolo sin verificarlos contra lo que manda el reloj.
- El diseño del panel está documentado en `DESIGN.md`; las decisiones y el protocolo verificado,
  en `CLAUDE.md`.

---

## Generar el .exe

### En la PC

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.venv\Scripts\python.exe -m PyInstaller mini-asistencia.spec --noconfirm
```

Sale en `dist\mini-asistencia.exe`: un solo archivo, sin consola, con el panel adentro.

### En GitHub Actions

El workflow `.github/workflows/build-windows.yml` corre en `windows-latest`:

1. Instala dependencias y corre los tests.
2. Genera el `.exe` con PyInstaller.
3. Comprueba que el `.exe` arranque y responda.
4. Lo publica como *artifact* (`mini-asistencia`) en cada push a `main` o al lanzarlo a mano
   (Actions → build-windows → Run workflow).
5. Con un tag `v*` crea además un **Release** con el `.exe` adjunto:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

---

## Protocolo del reloj

Verificado con un **ZKTeco Horus TL2** (reconocimiento facial, Wi-Fi, firmware
ZMM510-NF-Ver 1.0.21), que en "Config SVR de nube" solo ofrece modo ADMS. Es la variante PUSH
clásica (`iClock Proxy/1.09`):

| Request del reloj | Qué es | Respuesta |
|---|---|---|
| `GET /iclock/cdata?SN=..&options=all` | Saludo al conectarse | Opciones (`GET OPTION FROM: <SN>` + `clave=valor`) |
| `POST /iclock/cdata?SN=..&table=ATTLOG` | Marcaciones, una por línea separada por tab | `OK` |
| `POST /iclock/cdata?SN=..&table=OPERLOG` | Usuarios (`USER PIN=.. Name=..`) y operaciones | `OK` |
| `GET /iclock/getrequest?SN=..` | Consulta cada 2-5 s si hay comandos | `OK` o `C:<id>:<comando>` |
| `POST /iclock/devicecmd?SN=..` | Confirmación de un comando (`ID=..&Return=0`) | `OK` |

Comandos usados: `DATA UPDATE USERINFO PIN=..` (alta y modificación) y `DATA DELETE USERINFO PIN=..`
(baja), verificados con el reloj. El detalle completo y lo que todavía no está verificado están en
`CLAUDE.md`.

El reloj sube cada dato **una sola vez** (incremental): reiniciarlo no reenvía marcaciones ya
enviadas. Por eso no hay botón para "volver a pedir todo".

---

## Limitaciones conocidas

- Un solo reloj en uso (el panel manda los comandos al último que se conectó).
- El panel se ve solo desde la PC donde corre (no hay usuarios ni contraseñas).
- Sin turnos, horarios ni tolerancias: las horas son la suma de los pares entrada-salida.
- No se cruza la medianoche (el colegio es solo diurno).
- Arranca al iniciar sesión en Windows, no como servicio.
- El `.exe` no está firmado (aviso de SmartScreen y posibles falsos positivos de antivirus).
- No verificados todavía con el reloj: `Pri=14` = administrador, y si `Passwd=`/`Card=` vacíos
  borran una contraseña o tarjeta existente.
