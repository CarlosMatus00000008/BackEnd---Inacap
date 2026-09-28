/**
 * Diario de Viajes — tema claro / oscuro.
 *
 * Se carga en el <head>, ANTES del CSS y sin defer: así el tema queda puesto antes de
 * que se dibuje la página y no hay «parpadeo» de colores. (Es un archivo aparte, y no
 * un script escrito en el HTML, porque la política de seguridad CSP no permite scripts en línea.)
 *
 * - Si la persona eligió un tema con el interruptor, se usa ese (queda en localStorage).
 * - Si nunca eligió, se usa el de su sistema operativo, y cambia solo si el sistema cambia.
 * - La clave «theme» es la misma que usa el panel de administración de Django:
 *   así el sitio y el panel recuerdan la misma elección.
 */
(function () {
  "use strict";

  var CLAVE = "theme";
  var COLOR_BARRA = { light: "#f6f4ef", dark: "#12151c" }; // color de la barra del navegador en el celular
  var raiz = document.documentElement;
  var sistemaOscuro = window.matchMedia("(prefers-color-scheme: dark)");
  var sinAnimaciones = window.matchMedia("(prefers-reduced-motion: reduce)");

  function temaGuardado() {
    try {
      var valor = localStorage.getItem(CLAVE);
      return valor === "light" || valor === "dark" ? valor : null;
    } catch (error) {
      return null; // navegación privada o almacenamiento bloqueado
    }
  }

  function temaDelSistema() {
    return sistemaOscuro.matches ? "dark" : "light";
  }

  function actualizarInterruptores(tema) {
    var etiqueta = tema === "dark" ? "Cambiar a tema claro" : "Cambiar a tema oscuro";
    document.querySelectorAll("[data-cambiar-tema]").forEach(function (boton) {
      boton.setAttribute("aria-label", etiqueta);
      boton.setAttribute("title", etiqueta);
    });
  }

  function aplicar(tema) {
    raiz.setAttribute("data-theme", tema);
    document.querySelectorAll('meta[name="theme-color"]').forEach(function (meta) {
      meta.setAttribute("content", COLOR_BARRA[tema]);
    });
    actualizarInterruptores(tema);
  }

  function cambiar() {
    var nuevo = raiz.getAttribute("data-theme") === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(CLAVE, nuevo);
    } catch (error) {
      // Sin almacenamiento el cambio igual se aplica, solo que no se recuerda.
    }
    // Transición suave de colores solo durante el cambio (no al cargar cada página).
    if (!sinAnimaciones.matches) {
      raiz.classList.add("tema-en-transicion");
      window.setTimeout(function () {
        raiz.classList.remove("tema-en-transicion");
      }, 350);
    }
    aplicar(nuevo);
  }

  // 1) Antes de dibujar la página.
  aplicar(temaGuardado() || temaDelSistema());

  // 2) Si la persona nunca eligió, sigue al sistema en vivo (por ejemplo, al anochecer).
  sistemaOscuro.addEventListener("change", function () {
    if (!temaGuardado()) aplicar(temaDelSistema());
  });

  // 3) El interruptor de la barra superior (existe recién cuando se lee el <body>).
  document.addEventListener("DOMContentLoaded", function () {
    actualizarInterruptores(raiz.getAttribute("data-theme"));
  });
  document.addEventListener("click", function (evento) {
    if (evento.target.closest && evento.target.closest("[data-cambiar-tema]")) cambiar();
  });

  // 4) Si se cambia el tema en otra pestaña, esta también se actualiza.
  window.addEventListener("storage", function (evento) {
    if (evento.key === CLAVE) aplicar(temaGuardado() || temaDelSistema());
  });
})();
