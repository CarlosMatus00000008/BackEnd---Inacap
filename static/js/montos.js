/**
 * Punto de miles mientras escribes un monto: 1500000 → 1.500.000.
 *
 * Actúa sobre los <input data-monto> que dibujan MontoField y CantidadField (viajes/forms.py):
 *   data-monto="entero"   → pesos chilenos: solo cifras, sin decimales.
 *   data-monto="decimal"  → otras monedas: la coma (o el punto) marca los decimales, hasta 2.
 *
 * El punto de miles se agrega solo, así que no hace falta escribirlo. Si este archivo no carga,
 * el servidor igual entiende «25.000», «25000» o «12,50».
 */

const agruparMiles = (cifras) => cifras.replace(/^0+(?=\d)/, "").replace(/\B(?=(\d{3})+(?!\d))/g, ".");

const formatear = (texto, conDecimales) => {
  const limpio = texto.replace(conDecimales ? /[^\d,]/g : /\D/g, "");
  if (!limpio.includes(",")) return agruparMiles(limpio);
  const [entero, ...resto] = limpio.split(",");
  return `${agruparMiles(entero) || "0"},${resto.join("").slice(0, 2)}`;
};

// Un monto pegado o ya escrito puede venir como «1.500.000», «850000», «1500.50», «1,234.56» o «12,5».
// El último separador es decimal solo si le siguen 1 o 2 cifras; si no, todos son de miles.
const normalizar = (texto, conDecimales) => {
  const limpio = texto.replace(/[^\d.,]/g, "");
  const ultimo = Math.max(limpio.lastIndexOf(","), limpio.lastIndexOf("."));
  const fraccion = ultimo === -1 ? "" : limpio.slice(ultimo + 1);
  const tieneDecimales = ultimo !== -1 && /^\d{1,2}$/.test(fraccion);
  const entero = (tieneDecimales ? limpio.slice(0, ultimo) : limpio).replace(/\D/g, "");
  return tieneDecimales && conDecimales ? formatear(`${entero},${fraccion}`, true) : formatear(entero, conDecimales);
};

// Vuelve a dibujar el valor con sus puntos y deja el cursor donde estaba (contando solo cifras y la coma).
const reformatear = (campo, conDecimales) => {
  const util = conDecimales ? /[\d,]/ : /\d/;
  const antes = campo.value;
  const posicion = campo.selectionStart ?? antes.length;
  const utilesAntes = [...antes.slice(0, posicion)].filter((caracter) => util.test(caracter)).length;
  const nuevo = formatear(antes, conDecimales);
  if (nuevo === antes) return;

  campo.value = nuevo;
  let contados = 0;
  let cursor = 0;
  while (cursor < nuevo.length && contados < utilesAntes) {
    if (util.test(nuevo[cursor])) contados += 1;
    cursor += 1;
  }
  campo.setSelectionRange(cursor, cursor);
};

const activar = (campo) => {
  const conDecimales = campo.dataset.monto === "decimal";

  // Valor que viene del servidor (850000 o 110000.00) o de un envío con errores (850.000).
  campo.value = normalizar(campo.value, conDecimales);

  campo.addEventListener("beforeinput", (evento) => {
    if (evento.data !== "." && evento.data !== ",") return;
    evento.preventDefault(); // los puntos de miles se ponen solos
    if (conDecimales && !campo.value.includes(",")) {
      campo.setRangeText(",", campo.selectionStart, campo.selectionEnd, "end");
      reformatear(campo, conDecimales);
    }
  });

  campo.addEventListener("paste", (evento) => {
    evento.preventDefault();
    const pegado = normalizar(evento.clipboardData.getData("text"), conDecimales);
    campo.setRangeText(pegado, campo.selectionStart, campo.selectionEnd, "end");
    reformatear(campo, conDecimales);
  });

  campo.addEventListener("input", () => reformatear(campo, conDecimales));
};

for (const campo of document.querySelectorAll("input[data-monto]")) activar(campo);
