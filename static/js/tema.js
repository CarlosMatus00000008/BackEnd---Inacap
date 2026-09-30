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
 *
 * Es un script clásico (no un módulo) porque tiene que ejecutarse antes de dibujar la página;
 * la función que lo envuelve evita que sus constantes queden como variables globales.
 */
(() => {
  const CLAVE = "theme";
  const COLOR_BARRA = { light: "#f6f4ef", dark: "#12151c" }; // color de la barra del navegador en el celular
  const raiz = document.documentElement;
  const sistemaOscuro = window.matchMedia("(prefers-color-scheme: dark)");
  const sinAnimaciones = window.matchMedia("(prefers-reduced-motion: reduce)");

  const temaGuardado = () => {
    try {
      const valor = localStorage.getItem(CLAVE);
      return valor === "light" || valor === "dark" ? valor : null;
    } catch {
      return null; // navegación privada o almacenamiento bloqueado
    }
  };

  const temaDelSistema = () => (sistemaOscuro.matches ? "dark" : "light");

  const actualizarInterruptores = (tema) => {
    const etiqueta = tema === "dark" ? "Cambiar a tema claro" : "Cambiar a tema oscuro";
    for (const boton of document.querySelectorAll("[data-cambiar-tema]")) {
      boton.setAttribute("aria-label", etiqueta);
      boton.setAttribute("title", etiqueta);
    }
  };

  const aplicar = (tema) => {
    raiz.setAttribute("data-theme", tema);
    for (const meta of document.querySelectorAll('meta[name="theme-color"]')) {
      meta.setAttribute("content", COLOR_BARRA[tema]);
    }
    actualizarInterruptores(tema);
  };

  const cambiar = () => {
    const nuevo = raiz.getAttribute("data-theme") === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(CLAVE, nuevo);
    } catch {
      // Sin almacenamiento el cambio igual se aplica, solo que no se recuerda.
    }
    // Transición suave de colores solo durante el cambio (no al cargar cada página).
    if (!sinAnimaciones.matches) {
      raiz.classList.add("tema-en-transicion");
      setTimeout(() => raiz.classList.remove("tema-en-transicion"), 350);
    }
    aplicar(nuevo);
  };

  // 1) Antes de dibujar la página.
  aplicar(temaGuardado() ?? temaDelSistema());

  // 2) Si la persona nunca eligió, sigue al sistema en vivo (por ejemplo, al anochecer).
  sistemaOscuro.addEventListener("change", () => {
    if (!temaGuardado()) aplicar(temaDelSistema());
  });

  // 3) El interruptor de la barra superior (existe recién cuando se lee el <body>).
  document.addEventListener("DOMContentLoaded", () => actualizarInterruptores(raiz.getAttribute("data-theme")));
  document.addEventListener("click", (evento) => {
    if (evento.target.closest?.("[data-cambiar-tema]")) cambiar();
  });

  // 4) Si se cambia el tema en otra pestaña, esta también se actualiza.
  window.addEventListener("storage", (evento) => {
    if (evento.key === CLAVE) aplicar(temaGuardado() ?? temaDelSistema());
  });
})();
