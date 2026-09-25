/**
 * «Compartir con»: buscador de personas con sugerencias (patrón combobox de WAI-ARIA).
 *
 * Sin JavaScript el campo es un texto con nombres separados por coma y el servidor
 * valida cada nombre. Este módulo lo mejora:
 *   - desde la 2.ª letra muestra a las personas cuyo usuario o nombre empieza así
 *     (las entrega cuentas.views.BuscarUsuariosView),
 *   - cada persona elegida queda como una ficha que se puede quitar,
 *   - funciona con teclado: ↑ ↓ para moverse, Enter para elegir, Esc para cerrar
 *     y Retroceso (con el campo vacío) para quitar la última ficha,
 *   - un aviso para lectores de pantalla cuenta las sugerencias y los cambios.
 * Al enviar el formulario, las fichas se juntan otra vez como «pareja, admin».
 */

const ESPERA_MS = 180;
const MINIMO_LETRAS = 2;

// Crea elementos con textContent (nunca innerHTML): los nombres no pueden inyectar HTML.
const crear = (etiqueta, atributos = {}, ...hijos) => {
  const nodo = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(atributos)) {
    if (clave === "texto") nodo.textContent = valor;
    else nodo.setAttribute(clave, valor);
  }
  nodo.append(...hijos);
  return nodo;
};

const inicial = (texto) => (texto.trim()[0] || "?").toUpperCase();
const mismo = (a, b) => a.toLowerCase() === b.toLowerCase();
const personas = (n) => `${n} ${n === 1 ? "persona" : "personas"}`;

// Pone en negrita la parte que coincide con lo escrito («ad» → **ad**min).
const resaltar = (texto, buscado) =>
  texto.toLowerCase().startsWith(buscado.toLowerCase())
    ? [crear("mark", { texto: texto.slice(0, buscado.length) }), texto.slice(buscado.length)]
    : [texto];

function activar(campo) {
  const url = campo.dataset.buscarUsuarios;
  const maximo = Number(campo.dataset.maximo || 10);
  const elegidos = campo.value
    .split(",")
    .map((nombre) => nombre.trim())
    .filter(Boolean);

  // El valor viaja en un campo oculto; el campo visible queda solo para buscar.
  const oculto = crear("input", { type: "hidden", name: campo.name });
  campo.removeAttribute("name");
  campo.value = "";

  const fichas = crear("ul", { class: "selector-usuarios__fichas", "aria-label": "Compartido con" });
  const lista = crear("ul", {
    id: `${campo.id}_opciones`,
    class: "selector-usuarios__opciones",
    role: "listbox",
    "aria-label": "Personas sugeridas",
  });
  const aviso = crear("p", { class: "solo-lectores", "aria-live": "polite" });
  const caja = crear("div", { class: "selector-usuarios__caja" });
  const contenedor = crear("div", { class: "selector-usuarios" });
  lista.hidden = true;

  campo.replaceWith(contenedor);
  caja.append(fichas, campo);
  contenedor.append(caja, lista, aviso, oculto);

  Object.assign(campo, { autocomplete: "off", spellcheck: false, autocapitalize: "none" });
  campo.setAttribute("role", "combobox");
  campo.setAttribute("aria-autocomplete", "list");
  campo.setAttribute("aria-expanded", "false");
  campo.setAttribute("aria-controls", lista.id);

  const ayuda = document.getElementById(`${campo.id}_helptext`);
  if (ayuda && campo.dataset.ayuda) ayuda.textContent = campo.dataset.ayuda;

  let opciones = [];
  let activa = -1;
  let temporizador;
  let controlador;
  const memoria = new Map();

  /* --- Fichas y valor ---------------------------------------------------- */
  const sincronizar = () => {
    oculto.value = elegidos.join(", ");
    fichas.replaceChildren(
      ...elegidos.map((usuario) =>
        crear(
          "li",
          { class: "ficha-usuario" },
          crear("span", { class: "ficha-usuario__avatar", "aria-hidden": "true", texto: inicial(usuario) }),
          crear("span", { texto: usuario }),
          crear("button", {
            type: "button",
            class: "ficha-usuario__quitar",
            "data-usuario": usuario,
            "aria-label": `Quitar a ${usuario}`,
            title: `Quitar a ${usuario}`,
            texto: "×",
          }),
        ),
      ),
    );
    fichas.hidden = elegidos.length === 0;
    const lleno = elegidos.length >= maximo;
    campo.readOnly = lleno;
    if (lleno) campo.placeholder = `Llegaste al máximo de ${maximo} personas`;
    else campo.placeholder = elegidos.length ? "Agregar a otra persona…" : "Escribe un nombre de usuario…";
  };

  const resumen = () =>
    elegidos.length ? `Compartido con ${personas(elegidos.length)}.` : "No lo compartes con nadie.";

  const agregar = (usuario) => {
    if (!elegidos.some((e) => mismo(e, usuario)) && elegidos.length < maximo) {
      elegidos.push(usuario);
      aviso.textContent = `Agregaste a ${usuario}. ${resumen()}`;
    }
    campo.value = "";
    cerrar();
    sincronizar();
    campo.focus();
  };

  const quitar = (usuario) => {
    const indice = elegidos.findIndex((e) => mismo(e, usuario));
    if (indice === -1) return;
    elegidos.splice(indice, 1);
    sincronizar();
    aviso.textContent = `Quitaste a ${usuario}. ${resumen()}`;
    campo.focus();
  };

  /* --- Lista de sugerencias --------------------------------------------- */
  const abrir = () => {
    const estabaCerrada = lista.hidden;
    lista.hidden = false;
    campo.setAttribute("aria-expanded", "true");
    // En el celular la lista podría quedar bajo el teclado o la barra inferior.
    if (estabaCerrada) lista.scrollIntoView({ block: "nearest" });
  };

  function cerrar() {
    lista.hidden = true;
    activa = -1;
    campo.setAttribute("aria-expanded", "false");
    campo.removeAttribute("aria-activedescendant");
  }

  const mensaje = (texto) => {
    opciones = [];
    lista.replaceChildren(
      crear("li", { class: "selector-usuarios__vacio", role: "option", "aria-disabled": "true", texto }),
    );
    aviso.textContent = texto;
    abrir();
  };

  const marcar = (indice) => {
    const items = lista.querySelectorAll("[data-indice]");
    if (!items.length) return;
    activa = (indice + items.length) % items.length;
    items.forEach((item, i) => item.setAttribute("aria-selected", String(i === activa)));
    campo.setAttribute("aria-activedescendant", items[activa].id);
    items[activa].scrollIntoView({ block: "nearest" });
  };

  const mostrar = (resultados, buscado) => {
    opciones = resultados.filter((r) => !elegidos.some((e) => mismo(e, r.usuario)));
    activa = -1;
    campo.removeAttribute("aria-activedescendant");
    if (!opciones.length) {
      mensaje(
        resultados.length
          ? "Ya elegiste a todas las personas que coinciden."
          : `No hay usuarios que empiecen con «${buscado}».`,
      );
      return;
    }
    lista.replaceChildren(
      ...opciones.map((r, i) =>
        crear(
          "li",
          { id: `${campo.id}_opcion_${i}`, role: "option", "aria-selected": "false", "data-indice": i },
          crear("span", { class: "ficha-usuario__avatar", "aria-hidden": "true", texto: inicial(r.usuario) }),
          crear(
            "span",
            { class: "selector-usuarios__textos" },
            crear("strong", {}, ...resaltar(r.usuario, buscado)),
            r.nombre ? crear("small", {}, ...resaltar(r.nombre, buscado)) : "",
          ),
        ),
      ),
    );
    aviso.textContent = `${opciones.length} ${opciones.length === 1 ? "sugerencia" : "sugerencias"}. Usa las flechas para elegir.`;
    abrir();
  };

  /* --- Búsqueda en el servidor ------------------------------------------ */
  const pedir = async (texto) => {
    const clave = texto.toLowerCase();
    if (memoria.has(clave)) return memoria.get(clave);
    controlador?.abort();
    controlador = new AbortController();
    const respuesta = await fetch(`${url}?${new URLSearchParams({ q: texto })}`, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
      signal: controlador.signal,
    });
    if (!respuesta.ok || !respuesta.headers.get("content-type")?.includes("json")) {
      throw new Error(`Respuesta ${respuesta.status}`);
    }
    const { resultados = [] } = await respuesta.json();
    memoria.set(clave, resultados);
    return resultados;
  };

  const sinConexion = () =>
    mensaje("No pudimos buscar en este momento. Escribe el usuario completo; lo revisaremos al guardar.");

  const buscar = async () => {
    const texto = campo.value.trim();
    if (texto.length < MINIMO_LETRAS) {
      cerrar();
      return;
    }
    try {
      const resultados = await pedir(texto);
      if (campo.value.trim() === texto) mostrar(resultados, texto); // ignora respuestas atrasadas
    } catch (error) {
      if (error.name !== "AbortError") sinConexion();
    }
  };

  // Para lo escrito a mano (Enter, coma o pegar): solo se agrega si el usuario existe.
  const agregarEscrito = async (texto = campo.value) => {
    const nombre = texto.replaceAll(",", "").trim();
    if (!nombre) return;
    try {
      const exacto = (await pedir(nombre)).find((r) => mismo(r.usuario, nombre));
      if (exacto) agregar(exacto.usuario);
      else mensaje(`No encontramos a «${nombre}». Elige a la persona de la lista.`);
    } catch (error) {
      if (error.name !== "AbortError") sinConexion();
    }
  };

  /* --- Eventos ----------------------------------------------------------- */
  campo.addEventListener("input", () => {
    clearTimeout(temporizador);
    if (campo.value.trim().length < MINIMO_LETRAS) cerrar();
    else temporizador = setTimeout(buscar, ESPERA_MS);
  });

  campo.addEventListener("beforeinput", (evento) => {
    if (evento.data === ",") {
      evento.preventDefault();
      agregarEscrito();
    }
  });

  campo.addEventListener("paste", async (evento) => {
    const pegado = evento.clipboardData.getData("text");
    if (!pegado.includes(",")) return;
    evento.preventDefault();
    for (const nombre of pegado.split(",")) await agregarEscrito(nombre);
  });

  campo.addEventListener("keydown", (evento) => {
    switch (evento.key) {
      case "ArrowDown":
        evento.preventDefault();
        if (lista.hidden) buscar();
        else marcar(activa + 1);
        break;
      case "ArrowUp":
        evento.preventDefault();
        if (!lista.hidden) marcar(activa - 1);
        break;
      case "Enter":
        if (!campo.value.trim()) return; // campo vacío: Enter envía el formulario como siempre
        evento.preventDefault();
        if (!lista.hidden && activa >= 0) agregar(opciones[activa].usuario);
        else if (!lista.hidden && opciones.length === 1) agregar(opciones[0].usuario);
        else agregarEscrito();
        break;
      case "Escape":
        if (!lista.hidden) {
          evento.preventDefault();
          cerrar();
        }
        break;
      case "Backspace":
        if (!campo.value && elegidos.length) quitar(elegidos.at(-1));
        break;
      default:
    }
  });

  campo.addEventListener("focus", buscar);
  campo.addEventListener("blur", cerrar);

  // mousedown sin acción: elegir con el mouse no le quita el foco al campo.
  lista.addEventListener("mousedown", (evento) => evento.preventDefault());
  lista.addEventListener("click", (evento) => {
    const item = evento.target.closest("[data-indice]");
    if (item) agregar(opciones[Number(item.dataset.indice)].usuario);
  });

  fichas.addEventListener("click", (evento) => {
    const boton = evento.target.closest("[data-usuario]");
    if (boton) quitar(boton.dataset.usuario);
  });

  caja.addEventListener("click", (evento) => {
    if (evento.target === caja || evento.target === fichas) campo.focus();
  });

  // Lo que quedó escrito sin elegir también se envía, para que el servidor avise si no existe.
  campo.form?.addEventListener("submit", () => {
    const pendiente = campo.value.replaceAll(",", "").trim();
    oculto.value = [...elegidos, ...(pendiente ? [pendiente] : [])].join(", ");
  });

  sincronizar();
}

document.querySelectorAll("input[data-buscar-usuarios]").forEach(activar);
