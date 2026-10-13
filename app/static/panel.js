/* Panel de mini-asistencia: JS mínimo, sin dependencias (aparte de htmx).
   - Hoy: filtro por estado y buscador del lado del cliente; se conservan en la URL
     (?estado=&q=) y se vuelven a aplicar después de cada refresco de htmx.
   - Hoy: "entintado" de la hora cuando el refresco trae una marcación nueva.
   - Aviso si el panel deja de responder; estado de carga del botón de Excel.
   - Configuración: vista previa del logo y del nombre. */
(function () {
  "use strict";

  var ESTADOS = ["en_colegio", "se_retiro", "sin_marcar"];
  var estado = "";
  var q = "";
  var ultimas = null; // pin -> data-ultima del render anterior (null: todavía no hubo ninguno)

  function normalizar(texto) {
    return (texto || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  function leerUrl() {
    var params = new URLSearchParams(window.location.search);
    var e = params.get("estado") || "";
    estado = ESTADOS.indexOf(e) >= 0 ? e : "";
    q = params.get("q") || "";
  }

  function guardarUrl() {
    var params = new URLSearchParams();
    if (estado) params.set("estado", estado);
    if (q) params.set("q", q);
    var texto = params.toString();
    try {
      window.history.replaceState(null, "", window.location.pathname + (texto ? "?" + texto : ""));
    } catch (e) { /* sin historial: el filtro igual funciona */ }
  }

  function entintar(filas) {
    var actuales = {};
    filas.forEach(function (fila) {
      var pin = fila.dataset.pin;
      var ultima = fila.dataset.ultima;
      actuales[pin] = ultima;
      if (ultimas !== null && ultima && ultimas[pin] !== ultima) {
        var celda = fila.querySelector(".c-" + (fila.dataset.celda || "entrada"));
        if (celda) {
          celda.classList.remove("entintado");
          void celda.offsetWidth; // reinicia la animación si ya la tenía
          celda.classList.add("entintado");
        }
      }
    });
    ultimas = actuales;
  }

  function aplicar() {
    var hoy = document.getElementById("hoy");
    if (!hoy) return;
    hoy.dataset.filtro = estado;
    hoy.querySelectorAll(".segmento").forEach(function (boton) {
      boton.setAttribute("aria-pressed", String(boton.dataset.estado === estado));
    });
    var palabras = normalizar(q).split(/\s+/).filter(Boolean);
    var filas = Array.prototype.slice.call(hoy.querySelectorAll("tbody tr.fila"));
    var visibles = 0;
    filas.forEach(function (fila) {
      var texto = normalizar(fila.dataset.buscar);
      var coincide = (!estado || fila.dataset.estado === estado) &&
        palabras.every(function (palabra) { return texto.indexOf(palabra) >= 0; });
      fila.hidden = !coincide;
      if (coincide) visibles += 1;
    });
    var ninguno = hoy.querySelector(".ninguno");
    if (ninguno) ninguno.hidden = visibles > 0 || filas.length === 0;
    var limpiar = hoy.querySelector(".limpiar");
    if (limpiar) limpiar.hidden = !q;
    entintar(filas);
  }

  function quitarFiltros() {
    estado = "";
    q = "";
    var buscar = document.getElementById("buscar");
    if (buscar) {
      buscar.value = "";
      buscar.focus();
    }
    guardarUrl();
    aplicar();
  }

  function iniciarHoy() {
    var hoy = document.getElementById("hoy");
    if (!hoy) return;
    leerUrl();
    var buscar = document.getElementById("buscar");
    if (buscar) {
      buscar.value = q;
      buscar.addEventListener("input", function () {
        q = buscar.value;
        guardarUrl();
        aplicar();
      });
      buscar.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && buscar.value) {
          e.preventDefault();
          q = "";
          buscar.value = "";
          guardarUrl();
          aplicar();
        }
      });
    }
    hoy.addEventListener("click", function (e) {
      var segmento = e.target.closest(".segmento");
      if (segmento) {
        estado = segmento.dataset.estado;
        guardarUrl();
        aplicar();
      } else if (e.target.closest(".limpiar") || e.target.closest("[data-limpiar]")) {
        quitarFiltros();
      }
    });
    aplicar();
  }

  function iniciarAvisoDeConexion() {
    var aviso = document.getElementById("aviso-conexion");
    if (!aviso) return;
    document.body.addEventListener("htmx:afterRequest", function (e) {
      aviso.hidden = !!(e.detail && e.detail.successful);
    });
  }

  function iniciarDescarga() {
    document.addEventListener("click", function (e) {
      var boton = e.target.closest("[data-descarga]");
      if (!boton) return;
      boton.classList.add("cargando");
      boton.setAttribute("aria-busy", "true");
      window.setTimeout(function () {
        boton.classList.remove("cargando");
        boton.removeAttribute("aria-busy");
      }, 2500);
    });
  }

  function iniciarConfiguracion() {
    var logo = document.getElementById("logo");
    var nombre = document.getElementById("nombre");
    var previaNombre = document.getElementById("previa-nombre");
    if (nombre && previaNombre) {
      nombre.addEventListener("input", function () {
        previaNombre.textContent = nombre.value.trim() || "Nombre del colegio";
      });
    }
    if (!logo) return;
    var error = document.getElementById("logo-error");
    var url = null;
    logo.addEventListener("change", function () {
      var archivo = logo.files && logo.files[0];
      if (error) error.hidden = true;
      if (!archivo) return;
      if (archivo.size > Number(logo.dataset.max)) {
        if (error) {
          error.querySelector("span").textContent =
            "Ese archivo pesa más de 1 MB. Elegí una imagen más liviana.";
          error.hidden = false;
        }
        logo.value = "";
        return;
      }
      if (url) URL.revokeObjectURL(url);
      url = URL.createObjectURL(archivo);
      var imagen = document.getElementById("previa-img");
      var disco = document.getElementById("previa-disco");
      var vacia = document.getElementById("previa-vacia");
      if (imagen) { imagen.src = url; imagen.hidden = false; }
      if (disco) { disco.src = url; disco.hidden = false; }
      if (vacia) vacia.hidden = true;
    });
  }

  document.body.addEventListener("htmx:afterSwap", aplicar);
  iniciarHoy();
  iniciarAvisoDeConexion();
  iniciarDescarga();
  iniciarConfiguracion();
})();
