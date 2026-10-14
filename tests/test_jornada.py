from datetime import datetime, timedelta

from app import jornada
from app.jornada import (
  ANULADA, EN_COLEGIO, ENTRADA, REPETIDA, SALIDA, SE_RETIRO, SIN_MARCAR,
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


def test_de_a_pares_entrada_salida_entrada_salida():
  j = analizar([dt("17:00:00"), dt("08:00:00"), dt("12:00:00"), dt("13:00:00")])  # desordenadas
  assert j.momentos == [dt("08:00:00"), dt("12:00:00"), dt("13:00:00"), dt("17:00:00")]
  assert j.tipos == [ENTRADA, SALIDA, ENTRADA, SALIDA]
  assert (j.entrada, j.salida) == (dt("08:00:00"), dt("17:00:00"))
  assert j.pares == [(dt("08:00:00"), dt("12:00:00")), (dt("13:00:00"), dt("17:00:00"))]
  assert j.horas == timedelta(hours=8) and not j.abierta  # 4 h + 4 h, sin el hueco del medio


def test_impar_queda_abierta_y_el_par_abierto_no_suma_horas():
  j = analizar([dt("08:00:00"), dt("12:00:00"), dt("13:00:00")])
  assert j.tipos == [ENTRADA, SALIDA, ENTRADA] and j.abierta and j.salida is None
  assert j.pares[-1] == (dt("13:00:00"), None) and j.horas == timedelta(hours=4)


def test_tipos_cada_dia_empieza_con_entrada():
  filas = [marca("1", "08:00:00"), marca("1", "12:00:00"), marca("1", "13:00:00"),
           marca("1", "09:00:00", "2026-10-14"), marca("1", "15:00:00", "2026-10-14")]
  assert tipos_de_marcaciones(filas) == [ENTRADA, SALIDA, ENTRADA, ENTRADA, SALIDA]


def test_anulada_no_cuenta_y_las_demas_se_reacomodan():
  # Marcó 08:00, 08:05 (por error) y 17:00: sin anular, 17:00 sería una entrada sin salida
  filas = [marca("1", "08:00:00"), marca("1", "08:05:00"), marca("1", "17:00:00")]
  assert tipos_de_marcaciones(filas) == [ENTRADA, SALIDA, ENTRADA]
  filas[1]["anulada"] = "2026-10-13 18:00:00"
  assert tipos_de_marcaciones(filas) == [ENTRADA, ANULADA, SALIDA]
  f = vista_hoy([emp("1", "Zoe")], filas, datetime(2026, 10, 13, 18, 0)).filas[0]
  assert f.estado == SE_RETIRO and f.horas == timedelta(hours=9)


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
  assert (f.estado, f.entrada, f.salida, f.horas, f.tramos, f.ultima, f.celda_nueva) == (
    SIN_MARCAR, None, None, None, [], "", "")


def test_repetida_no_cambia_el_estado_ni_la_ultima():
  f = vista_hoy([emp("3", "Beto")], [marca("3", "07:30:00"), marca("3", "07:31:00")], AHORA).filas[0]
  assert f.estado == EN_COLEGIO and f.repetidas == 1 and f.ultima == "2026-10-13 07:30:00"


def test_salio_y_volvio_un_tramo_por_par_y_horas_hasta_ahora():
  marcas = [marca("1", "07:30:00"), marca("1", "08:30:00"), marca("1", "09:30:00")]
  f = vista_hoy([emp("1", "Zoe")], marcas, AHORA).filas[0]
  assert f.estado == EN_COLEGIO and f.salida is None and f.horas_parcial
  assert f.horas == timedelta(hours=2)  # 07:30-08:30 + 09:30-10:30 (ahora)
  assert [t.abierto for t in f.tramos] == [False, True]
  assert f.ultima == "2026-10-13 09:30:00" and f.celda_nueva == "entrada"


def test_dos_pares_se_retiro_con_la_ultima_salida():
  marcas = [marca("1", "08:00:00"), marca("1", "09:00:00"), marca("1", "09:30:00"),
            marca("1", "10:00:00")]
  f = vista_hoy([emp("1", "Zoe")], marcas, AHORA).filas[0]
  assert f.estado == SE_RETIRO and f.salida == dt("10:00:00") and not f.horas_parcial
  assert f.horas == timedelta(hours=1, minutes=30) and len(f.tramos) == 2


def test_posiciones_en_la_franja_de_las_7_a_las_19():
  v = vista_hoy([emp("1", "Zoe"), emp("2", "Beto")],
                [marca("1", "07:30:00"), marca("1", "13:00:00"), marca("2", "07:00:00")], AHORA)
  zoe, beto = por_pin(v)["1"], por_pin(v)["2"]
  assert zoe.tramos[0] == jornada.Tramo(4.167, 45.833, False, False, False)  # 07:30 -> 13:00
  # Beto: de 07:00 hasta ahora (10:30): extremo abierto
  assert beto.tramos[0] == jornada.Tramo(0.0, 29.167, True, False, False)
  assert v.ahora_pct == 29.167


def test_fuera_de_la_franja_se_recorta_al_borde_y_se_indica():
  v = vista_hoy([emp("1", "Madrugador"), emp("2", "Tarde")],
                [marca("1", "06:30:00"), marca("1", "19:30:00"),
                 marca("2", "20:00:00")], datetime(2026, 10, 13, 21, 0))
  madrugador, tarde = por_pin(v)["1"], por_pin(v)["2"]
  assert madrugador.tramos[0] == jornada.Tramo(0.0, 100.0, False, True, True)
  # Entró a las 20:00 y sigue: todo queda a la derecha de la franja
  assert tarde.tramos[0].izq == 100.0 and tarde.tramos[0].ancho == 0.0
  assert tarde.tramos[0].abierto and tarde.tramos[0].recorte_der
  assert v.ahora_pct is None  # son las 21:00: la línea "ahora" no se dibuja


def test_la_linea_ahora_no_se_dibuja_antes_de_las_7():
  assert vista_hoy([], [], datetime(2026, 10, 13, 6, 59)).ahora_pct is None
  assert vista_hoy([], [], datetime(2026, 10, 13, 7, 0)).ahora_pct == 0.0
  assert vista_hoy([], [], datetime(2026, 10, 13, 19, 0)).ahora_pct == 100.0


# --- Última marcación (el renglón vivo de Hoy) ---------------------------------------------

def test_ultima_marcacion_es_la_valida_mas_reciente_de_todos():
  empleados = [emp("1", "Zoe"), emp("3", "Beto")]
  marcas = [marca("1", "08:00:00"), marca("1", "09:30:00"),   # Zoe se retiró 09:30
            marca("3", "07:30:00"), marca("3", "09:10:00")]   # Beto se retiró 09:10
  u = vista_hoy(empleados, marcas, AHORA).ultima
  assert (u.pin, u.nombre, u.tipo, u.hora) == ("1", "Zoe", "Salida", "09:30")
  assert u.clave == "1|2026-10-13 09:30:00"
  # llega alguien nuevo (entrada): pasa a ser la última y la clave cambia
  nueva = vista_hoy(empleados, marcas + [marca("2", "10:05:07")], AHORA).ultima
  assert (nueva.pin, nueva.nombre, nueva.tipo, nueva.hora) == ("2", None, "Entrada", "10:05")
  assert nueva.clave != u.clave


def test_ultima_marcacion_ignora_repetidas_y_dias_anteriores():
  marcas = [marca("3", "07:30:00"), marca("3", "07:31:00"),
            marca("3", "23:00:00", dia="2026-10-12")]
  u = vista_hoy([emp("3", "Beto")], marcas, AHORA).ultima
  assert (u.tipo, u.hora) == ("Entrada", "07:30")


def test_sin_marcaciones_no_hay_ultima():
  assert vista_hoy([emp("3", "Beto")], [], AHORA).ultima is None

