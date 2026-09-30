/**
 * Diario de Viajes — mejoras progresivas.
 * El sitio funciona completo sin JavaScript; este archivo solo agrega comodidades.
 * Se carga como módulo (type="module"): se ejecuta cuando la página ya está lista.
 *
 * Otros módulos del sitio (se cargan en base.html):
 *   buscador-usuarios.js  → sugerencias al compartir un viaje con otra persona
 */

const HOY = new Date().toLocaleDateString("en-CA"); // AAAA-MM-DD en la zona horaria local

/* 1. Alertas: botón de cerrar y ocultado automático de los mensajes de éxito. */
document.addEventListener("click", (evento) => {
  const boton = evento.target.closest("[data-cerrar-alerta]");
  if (boton) boton.closest(".alerta")?.remove();
});

document.querySelectorAll(".alertas .alerta--exito").forEach((alerta) => {
  setTimeout(() => alerta.remove(), 8000);
});

/* 2. Formulario de viaje: sugiere el estado según las fechas y ajusta la fecha mínima de regreso. */
const formularioViaje = document.querySelector("[data-formulario-viaje]");

if (formularioViaje) {
  const inicio = formularioViaje.querySelector("#id_fecha_inicio");
  const regreso = formularioViaje.querySelector("#id_fecha_fin");
  let estadoElegidoAMano = formularioViaje.dataset.edicion === "true";

  formularioViaje.querySelectorAll('input[name="estado"]').forEach((opcion) => {
    opcion.addEventListener("change", () => {
      estadoElegidoAMano = true;
    });
  });

  const actualizar = () => {
    if (regreso && inicio.value) regreso.min = inicio.value;
    if (estadoElegidoAMano || !inicio.value) return;

    let sugerido = "planificado";
    if (inicio.value <= HOY) {
      sugerido = regreso?.value && regreso.value < HOY ? "completado" : "en_progreso";
    }
    const opcion = formularioViaje.querySelector(`input[name="estado"][value="${sugerido}"]`);
    if (opcion) opcion.checked = true;
  };

  inicio?.addEventListener("change", actualizar);
  regreso?.addEventListener("change", actualizar);
}

/* 3. Evita envíos dobles: desactiva el botón mientras se procesa el formulario. */
document.addEventListener("submit", (evento) => {
  const formulario = evento.target;
  if (!(formulario instanceof HTMLFormElement) || formulario.method.toLowerCase() !== "post") return;
  const boton = evento.submitter;
  if (boton && !formulario.hasAttribute("data-permitir-reenvio")) {
    setTimeout(() => {
      boton.disabled = true;
      boton.setAttribute("aria-busy", "true");
    }, 0);
  }
});

// Si el usuario vuelve atrás con el navegador, los botones quedan habilitados otra vez.
window.addEventListener("pageshow", (evento) => {
  if (!evento.persisted) return;
  document.querySelectorAll('button[aria-busy="true"]').forEach((boton) => {
    boton.disabled = false;
    boton.removeAttribute("aria-busy");
  });
});

/* 4. Registro: consentimiento de datos personales.
      - Al hacer clic en la casilla (o en su texto) NO se marca: se abre la ventana informativa.
      - «Aceptar» la marca; «Rechazar», Esc o un clic fuera la dejan desmarcada.
      - El botón «Crear cuenta» queda deshabilitado mientras la casilla no esté marcada.
      Sin JavaScript la casilla funciona normal y el servidor igual exige marcarla. */
const abrirDialogo = (dialogo) => {
  dialogo.returnValue = ""; // así Esc o un clic fuera cuentan como «rechazar»
  dialogo.showModal();
};

document.addEventListener("click", (evento) => {
  const enlace = evento.target.closest("[data-abrir-dialogo]");
  if (!enlace) return;
  const dialogo = document.getElementById(enlace.dataset.abrirDialogo);
  if (!(dialogo instanceof HTMLDialogElement)) return;
  evento.preventDefault();
  abrirDialogo(dialogo);
});

const formularioConsentimiento = document.querySelector("[data-formulario-consentimiento]");
const dialogoConsentimiento = document.querySelector("dialog[data-consentimiento-para]");

if (formularioConsentimiento && dialogoConsentimiento) {
  const casilla = document.getElementById(dialogoConsentimiento.dataset.consentimientoPara);
  const botonEnviar = formularioConsentimiento.querySelector('button[type="submit"]');

  const sincronizar = () => {
    if (casilla && botonEnviar) botonEnviar.disabled = !casilla.checked;
  };

  // Cualquier cambio hecho por la persona (clic, tecla espacio) desmarca y abre la ventana.
  casilla?.addEventListener("change", () => {
    casilla.checked = false;
    sincronizar();
    abrirDialogo(dialogoConsentimiento);
  });

  dialogoConsentimiento.addEventListener("close", () => {
    if (casilla) casilla.checked = dialogoConsentimiento.returnValue === "aceptar";
    sincronizar();
  });

  window.addEventListener("pageshow", sincronizar);
  sincronizar();
}

// Un clic fuera de la ventana (sobre el fondo oscurecido) también la cierra.
document.querySelectorAll("dialog.dialogo").forEach((dialogo) => {
  dialogo.addEventListener("click", (evento) => {
    if (evento.target === dialogo) dialogo.close();
  });
});

/* 5. Mis viajes: el mapa mundi se despliega hacia abajo con una animación.
      Sin JavaScript (o con «reducir movimiento») el <details> se abre y cierra de golpe. */
const mapaMundi = document.querySelector("[data-mapa-mundi]");
const reducirMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)");

if (mapaMundi) {
  const contenido = mapaMundi.querySelector(".mapa-mundi__contenido");
  let animacion = null;
  let abierto = mapaMundi.open;

  mapaMundi.querySelector("summary").addEventListener("click", (evento) => {
    if (reducirMovimiento.matches) return;
    evento.preventDefault();

    // Si se hace clic a mitad de la animación, parte desde la altura actual.
    const desde = mapaMundi.open ? contenido.getBoundingClientRect().height : 0;
    animacion?.cancel();
    abierto = !abierto;
    mapaMundi.open = true;
    const hasta = abierto ? contenido.getBoundingClientRect().height : 0;

    animacion = contenido.animate(
      [
        { height: `${desde}px`, opacity: desde ? 1 : 0 },
        { height: `${hasta}px`, opacity: abierto ? 1 : 0 },
      ],
      { duration: 420, easing: "cubic-bezier(0.2, 0.7, 0.2, 1)" },
    );
    animacion.onfinish = () => {
      animacion = null;
      mapaMundi.open = abierto;
    };
  });
}

/* 6. Mapa mundi interactivo: al pasar el mouse por un país visitado (o enfocarlo con el
      teclado) aparece una tarjeta con sus viajes. En pantallas táctiles el primer toque
      muestra la tarjeta y el segundo abre el viaje. Sin JavaScript, el clic abre el viaje. */
const lienzoMapa = document.querySelector("[data-mapa-lienzo]");

if (lienzoMapa) {
  let tarjeta = null;
  let tipoPuntero = "mouse"; // "mouse", "touch", "pen" o "teclado"
  let tocado = null; // último país tocado en pantalla táctil
  const esTactil = () => tipoPuntero === "touch" || tipoPuntero === "pen";

  const paisDe = (evento) => evento.target.closest?.("[data-mapa-pais]");

  // Junto al puntero, sin salirse del mapa: si no cabe a la derecha, va a la izquierda.
  const ubicar = (x, y) => {
    const caja = lienzoMapa.getBoundingClientRect();
    const margen = 14;
    let izquierda = x - caja.left + margen;
    let arriba = y - caja.top + margen;
    if (izquierda + tarjeta.offsetWidth > caja.width) izquierda = x - caja.left - tarjeta.offsetWidth - margen;
    if (arriba + tarjeta.offsetHeight > caja.height) arriba = caja.height - tarjeta.offsetHeight;
    tarjeta.style.left = `${Math.max(0, izquierda)}px`;
    tarjeta.style.top = `${Math.max(0, arriba)}px`;
  };

  // Bandera y nombre del país, arriba del mapa
  const marcarEtiqueta = (id) => {
    for (const etiqueta of lienzoMapa.querySelectorAll("[data-mapa-etiqueta]")) {
      etiqueta.classList.toggle("activo", etiqueta.dataset.mapaEtiqueta === id);
    }
  };

  const mostrar = (pais, x, y) => {
    const nueva = document.getElementById(pais.dataset.mapaPais);
    if (tarjeta && tarjeta !== nueva) tarjeta.hidden = true;
    if (tarjeta !== nueva) marcarEtiqueta(nueva.id);
    tarjeta = nueva;
    tarjeta.hidden = false;
    ubicar(x, y);
  };

  const ocultar = () => {
    if (tarjeta) tarjeta.hidden = true;
    tarjeta = null;
    tocado = null;
    marcarEtiqueta(null);
  };

  const centroDe = (pais) => {
    const caja = pais.getBoundingClientRect();
    return [caja.left + caja.width / 2, caja.top + caja.height / 2];
  };

  lienzoMapa.addEventListener("pointerdown", (evento) => {
    tipoPuntero = evento.pointerType;
  });

  lienzoMapa.addEventListener("pointermove", (evento) => {
    if (evento.pointerType !== "mouse") return;
    const pais = paisDe(evento);
    if (pais) mostrar(pais, evento.clientX, evento.clientY);
    else ocultar();
  });

  lienzoMapa.addEventListener("pointerleave", (evento) => {
    if (evento.pointerType === "mouse") ocultar();
  });

  lienzoMapa.addEventListener("focusin", (evento) => {
    const pais = paisDe(evento);
    if (pais && !esTactil()) mostrar(pais, ...centroDe(pais));
  });

  lienzoMapa.addEventListener("focusout", (evento) => {
    if (!lienzoMapa.contains(evento.relatedTarget)) ocultar();
  });

  lienzoMapa.addEventListener("click", (evento) => {
    if (!esTactil()) return;
    const pais = paisDe(evento);
    if (!pais) return ocultar();
    if (tocado === pais) return; // segundo toque: sigue el enlace
    evento.preventDefault();
    mostrar(pais, ...centroDe(pais));
    tocado = pais;
  });

  document.addEventListener("keydown", (evento) => {
    tipoPuntero = "teclado";
    if (evento.key === "Escape") ocultar();
  });
}

/* 7. Detalle del viaje: las fotos pasan de fondo en la portada. Cada 3 segundos la foto
      actual se desliza a la derecha y entra la siguiente desde la izquierda. Cada foto se
      descarga justo antes de su turno. Con «reducir movimiento» queda la primera fija. */
const carrusel = document.querySelector("[data-carrusel]");

if (carrusel && !reducirMovimiento.matches) {
  const fotos = [...carrusel.querySelectorAll("img")];
  let actual = 0;

  const cargar = (foto) => {
    if (foto.dataset.src) {
      foto.src = foto.dataset.src;
      delete foto.dataset.src;
    }
  };

  const avanzar = () => {
    const siguiente = fotos[(actual + 1) % fotos.length];
    if (document.hidden || !siguiente.complete) return; // espera a que la siguiente esté descargada
    const saliente = fotos[actual];
    const opciones = { duration: 1000, easing: "cubic-bezier(0.65, 0, 0.35, 1)" };
    siguiente.classList.add("activa");
    siguiente.animate([{ translate: "-100% 0" }, { translate: "0 0" }], opciones);
    saliente.animate([{ translate: "0 0" }, { translate: "100% 0" }], opciones).onfinish = () =>
      saliente.classList.remove("activa");
    actual = fotos.indexOf(siguiente);
    cargar(fotos[(actual + 1) % fotos.length]);
  };

  if (fotos.length > 1) {
    cargar(fotos[1]);
    setInterval(avanzar, 3000);
  }
}
