from datetime import datetime, timedelta

from app import jornada
from app.jornada import (
  EN_COLEGIO, ENTRADA, INTERMEDIA, REPETIDA, SALIDA, SE_RETIRO, SIN_MARCAR,
  analizar, fecha_larga, fmt_horas, tipos_de_marcaciones, vista_hoy,
)

DIA = "2026-10-13"
AHORA = datetime(2026, 10, 13, 10, 30)


def dt(hora, dia=DIA):
  return datetime.fromisoformat(f"{dia} {hora}")


def emp(pin, nombre):
  return {"pin": pin, "nombre": nombre}


def marca(pin, hora, dia=DIA):
  return {"pin": pin, "fecha_hora": f"{dia} {hora}"}


def por_pin(vista):
  return {f.pin: f for f in vista.filas}


# --- analizar: la regla única ---------------------------------------------------------------

def test_sin_marcaciones():
  j = analizar([])
  assert (j.entrada, j.salida, j.validas, j.tipos, j.repetidas) == (None, None, [], [], 0)


def test_una_marcacion_es_entrada_sin_salida():
  j = analizar([dt("08:00:00")])
  assert j.tipos == [ENTRADA] and j.entrada == dt("08:00:00") and j.salida is None


def test_primera_entrada_ultima_salida_intermedias_en_el_medio():
  j = analizar([dt("17:00:00"), dt("08:00:00"), dt("12:00:00"), dt("13:00:00")])  # desordenadas
  assert j.momentos == [dt("08:00:00"), dt("12:00:00"), dt("13:00:00"), dt("17:00:00")]
  assert j.tipos == [ENTRADA, INTERMEDIA, INTERMEDIA, SALIDA]
  assert (j.entrada, j.salida) == (dt("08:00:00"), dt("17:00:00"))
  assert j.intermedias == [dt("12:00:00"), dt("13:00:00")]


def test_repetidas_a_menos_de_2_minutos_se_ignoran():
  j = analizar([dt("08:00:00"), dt("08:01:59"), dt("17:00:00"), dt("17:00:30")])
  assert j.tipos == [ENTRADA, REPETIDA, SALIDA, REPETIDA]
  assert j.repetidas == 2 and j.validas == [dt("08:00:00"), dt("17:00:00")]
  # justo 2 minutos ya cuenta
  assert analizar([dt("08:00:00"), dt("08:02:00")]).tipos == [ENTRADA, SALIDA]


def test_solo_repetidas_queda_en_el_colegio():
  j = analizar([dt("08:00:00"), dt("08:00:40")])
  assert j.tipos == [ENTRADA, REPETIDA] and j.salida is None


def test_repetida_se_mide_contra_la_ultima_valida_no_contra_la_ignorada():
  # 08:00 válida, 08:01:30 repetida, 08:03 ya está a >2 min de la última VÁLIDA
  j = analizar([dt("08:00:00"), dt("08:01:30"), dt("08:03:00")])
  assert j.tipos == [ENTRADA, REPETIDA, SALIDA]


def test_tipos_de_marcaciones_agrupa_por_dia_y_pin_en_cualquier_orden():
  filas = [
    {"pin": "7", "fecha_hora": "2026-10-12 17:00:00"},
    {"pin": "7", "fecha_hora": "2026-10-12 08:00:00"},
    {"pin": "8", "fecha_hora": "2026-10-12 09:00:00"},
    {"pin": "7", "fecha_hora": "2026-10-13 08:00:00"},
    {"pin": "7", "fecha_hora": "2026-10-12 08:00:20"},
  ]
  assert tipos_de_marcaciones(filas) == [SALIDA, ENTRADA, ENTRADA, ENTRADA, REPETIDA]


# --- Formato ---------------------------------------------------------------------------------

def test_fecha_larga_en_castellano():
  assert fecha_larga(datetime(2026, 10, 13)) == "Martes 13 de octubre"
  assert fecha_larga(datetime(2026, 3, 1)) == "Domingo 1 de marzo"
  assert fecha_larga(datetime(2026, 9, 9)) == "Miércoles 9 de septiembre"


def test_fmt_horas_hmm_con_minutos_hacia_abajo():
  assert fmt_horas(timedelta(hours=7, minutes=48, seconds=59)) == "7:48"
  assert fmt_horas(timedelta(0)) == "0:00" and fmt_horas(timedelta(hours=10, minutes=5)) == "10:05"
  assert fmt_horas(None) == "" and fmt_horas(timedelta(minutes=-5)) == "0:00"


# --- vista_hoy -------------------------------------------------------------------------------

def test_estados_conteos_y_orden():
  empleados = [emp("1", "Zoe"), emp("2", "Ana"), emp("3", "Beto"), emp("4", "Álvaro"),
               emp("5", "Carla")]
  marcas = [
    marca("1", "08:00:00"), marca("1", "16:00:00"),   # Zoe: se retiró
    marca("3", "07:30:00"),                            # Beto: en el colegio
    marca("5", "09:00:00"),                            # Carla: en el colegio
    marca("77", "08:30:00"),                           # PIN que no está en empleados
    marca("2", "20:00:00", dia="2026-10-12"),          # Ana marcó ayer, hoy nada
  ]
  v = vista_hoy(empleados, marcas, AHORA)
  assert [f.pin for f in v.filas] == ["3", "1", "77", "5", "4", "2"]
  # En el colegio y se retiró juntos por hora de entrada; sin marcar al final por nombre
  # (Álvaro antes que Ana: el orden ignora las tildes)
  assert [f.estado for f in v.filas] == [
    EN_COLEGIO, SE_RETIRO, EN_COLEGIO, EN_COLEGIO, SIN_MARCAR, SIN_MARCAR]
  assert v.conteos == {"todos": 6, EN_COLEGIO: 3, SE_RETIRO: 1, SIN_MARCAR: 2}


def test_pin_con_marcaciones_pero_sin_empleado_se_muestra_sin_nombre():
  f = por_pin(vista_hoy([], [marca("7", "08:00:00")], AHORA))["7"]
  assert f.nombre is None and f.estado == EN_COLEGIO


def test_sin_nadie():
  v = vista_hoy([], [], AHORA)
  assert v.filas == [] and v.conteos["todos"] == 0


def test_entrada_salida_horas_y_ultima_de_quien_se_retiro():
  f = por_pin(vista_hoy([emp("1", "Zoe")], [marca("1", "08:00:00"), marca("1", "16:30:40")],
                        AHORA))["1"]
  assert (f.entrada, f.salida) == (dt("08:00:00"), dt("16:30:40"))
  assert f.horas == timedelta(hours=8, minutes=30, seconds=40) and not f.horas_parcial
  assert f.ultima == "2026-10-13 16:30:40" and f.celda_nueva == "salida"


def test_horas_hasta_ahora_de_quien_sigue_en_el_colegio():
  v = vista_hoy([emp("3", "Beto")], [marca("3", "07:30:00")], AHORA)
  f = v.filas[0]
  assert f.horas == timedelta(hours=3) and f.horas_parcial and f.salida is None
  assert f.ultima == "2026-10-13 07:30:00" and f.celda_nueva == "entrada"
  # El tiempo se inyecta: una hora después son 4 h
  assert vista_hoy([emp("3", "Beto")], [marca("3", "07:30:00")],
                   AHORA + timedelta(hours=1)).filas[0].horas == timedelta(hours=4)


def test_reloj_de_la_pc_atrasado_no_da_horas_negativas():
  f = vista_hoy([emp("3", "Beto")], [marca("3", "11:00:00")], AHORA).filas[0]
  assert f.horas == timedelta(0)


def test_sin_marcar_no_tiene_horas_ni_tramo():
  f = vista_hoy([emp("2", "Ana")], [], AHORA).filas[0]
  assert (f.estado, f.entrada, f.salida, f.horas, f.tramo, f.ticks, f.ultima, f.celda_nueva) == (
    SIN_MARCAR, None, None, None, None, [], "", "")


def test_repetida_no_cambia_el_estado_ni_la_ultima():
  f = vista_hoy([emp("3", "Beto")], [marca("3", "07:30:00"), marca("3", "07:31:00")], AHORA).filas[0]
  assert f.estado == EN_COLEGIO and f.repetidas == 1 and f.ultima == "2026-10-13 07:30:00"


def test_intermedias_son_ticks_y_la_ultima_valida_es_la_salida():
  marcas = [marca("1", "08:00:00"), marca("1", "12:00:00"), marca("1", "16:00:00")]
  f = vista_hoy([emp("1", "Zoe")], marcas, AHORA).filas[0]
  assert f.estado == SE_RETIRO and f.salida == dt("16:00:00")
  assert f.ticks == [41.667]  # 12:00 en la franja de 07:00 a 19:00
  assert f.ultima == "2026-10-13 16:00:00" and f.celda_nueva == "salida"


def test_posiciones_en_la_franja_de_las_7_a_las_19():
  v = vista_hoy([emp("1", "Zoe"), emp("2", "Beto")],
                [marca("1", "07:30:00"), marca("1", "13:00:00"), marca("2", "07:00:00")], AHORA)
  zoe, beto = por_pin(v)["1"], por_pin(v)["2"]
  assert zoe.tramo == jornada.Tramo(4.167, 45.833, False, False, False)  # 07:30 -> 13:00
  # Beto: de 07:00 hasta ahora (10:30): extremo abierto
  assert beto.tramo == jornada.Tramo(0.0, 29.167, True, False, False)
  assert v.ahora_pct == 29.167


def test_fuera_de_la_franja_se_recorta_al_borde_y_se_indica():
  v = vista_hoy([emp("1", "Madrugador"), emp("2", "Tarde")],
                [marca("1", "06:30:00"), marca("1", "19:30:00"),
                 marca("2", "20:00:00")], datetime(2026, 10, 13, 21, 0))
  madrugador, tarde = por_pin(v)["1"], por_pin(v)["2"]
  assert madrugador.tramo == jornada.Tramo(0.0, 100.0, False, True, True)
  # Entró a las 20:00 y sigue: todo queda a la derecha de la franja
  assert tarde.tramo.izq == 100.0 and tarde.tramo.ancho == 0.0
  assert tarde.tramo.abierto and tarde.tramo.recorte_der
  assert v.ahora_pct is None  # son las 21:00: la línea "ahora" no se dibuja


def test_la_linea_ahora_no_se_dibuja_antes_de_las_7():
  assert vista_hoy([], [], datetime(2026, 10, 13, 6, 59)).ahora_pct is None
  assert vista_hoy([], [], datetime(2026, 10, 13, 7, 0)).ahora_pct == 0.0
  assert vista_hoy([], [], datetime(2026, 10, 13, 19, 0)).ahora_pct == 100.0
