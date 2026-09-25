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
