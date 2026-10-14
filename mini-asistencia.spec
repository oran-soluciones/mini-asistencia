# PyInstaller: un único mini-asistencia.exe, sin consola, con el panel (templates y static) adentro.
# Uso: .venv\Scripts\python.exe -m PyInstaller mini-asistencia.spec --noconfirm
# Sale en dist\mini-asistencia.exe (lo mismo hace .github/workflows/build-windows.yml).
from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
  ["app/main.py"],
  pathex=["."],
  datas=[("app/templates", "app/templates"), ("app/static", "app/static")],
  # uvicorn carga su loop y protocolos por nombre; pystray elige el backend de Windows al vuelo
  hiddenimports=collect_submodules("uvicorn") + collect_submodules("pystray") + ["app.panel"],
  excludes=["tkinter", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(
  pyz,
  a.scripts,
  a.binaries,
  a.datas,
  name="mini-asistencia",
  icon="app/static/icono.ico",
  console=False,
  upx=False,  # UPX dispara más falsos positivos de antivirus
)
