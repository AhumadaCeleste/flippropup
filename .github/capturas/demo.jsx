// Página de demostración con datos de ejemplo (solo para sacar capturas en GitHub Actions; no se publica).
import Tarjeta from "@/components/Tarjeta";
import MapaResultados from "@/components/MapaResultados";
import Relevar from "@/components/Relevar";

const EJEMPLOS = [
  { id: 1, portal: "cordobaprop", url: "https://www.cordobaprop.com/propiedad/3138", titulo: "Allende suite depto a estrenar frente a los Aroza", precio: 65000, moneda: "USD",
    foto_principal: "https://cordobaprop.com/content/images/3138_0.jpg", barrio: "Villa Allende Centro", ciudad: "Villa Allende", dormitorios: "1 Dormitorio",
    superficie_total: 40, precio_m2: 1625, vendedor_tipo: "Inmobiliaria", vendedor_nombre: "Salsadella", telefono: "5493516599905", lat: -31.4116, lng: -64.1772, primera_vez: new Date().toISOString() },
  { id: 2, portal: "inmobiliarias", url: "https://www.bergo.com.ar/p/8054863", titulo: "Departamento en Venta en Villa Belgrano · Calle Pública S/N", precio: 180000, moneda: "USD",
    foto_principal: "https://static.tokkobroker.com/w_pics/8054863_23971231407904572111052532476659047445459670690294959076092709455178560075666.jpg",
    barrio: "Villa Belgrano", ciudad: "Córdoba", dormitorios: "1 Dormitorio", superficie_total: 69, precio_m2: 2609, vendedor_tipo: "Inmobiliaria",
    vendedor_nombre: "Bergo Servicios Inmobiliarios", telefono: "5493513863291", lat: -31.3700, lng: -64.2370, primera_vez: new Date().toISOString() },
  { id: 3, portal: "mercadolibre", url: "https://departamento.mercadolibre.com.ar/MLA-2686089882", titulo: "Torre Aurus Nueva Córdoba", precio: 112000, moneda: "USD",
    foto_principal: "https://http2.mlstatic.com/D_NQ_NP_2X_601280-MLA101170501652_122025-E.webp", barrio: "Nueva Córdoba", ciudad: "Córdoba",
    dormitorios: "1 Dormitorio", superficie_total: 44, precio_m2: 2545, vendedor_tipo: "Inmobiliaria", vendedor_nombre: "Inmobiliaria Malbran", lat: -31.4240, lng: -64.1880, primera_vez: new Date().toISOString() },
  { id: 4, portal: "lavoz", url: "https://clasificados.lavoz.com.ar/avisos/inmuebles/departamento/5599263", titulo: "Dueño vende depto 1 dorm con balcón, Alberdi", precio: 58000, moneda: "USD",
    foto_principal: "https://static.tokkobroker.com/w_pics/8054863_23971231407904572111052532476659047445459670690294959076092709455178560075666.jpg",
    barrio: "Alberdi", ciudad: "Córdoba", dormitorios: "1 Dormitorio", superficie_total: 42, precio_m2: 1381, vendedor_tipo: "Particular", telefono: "5493514223344", lat: -31.4080, lng: -64.2050, primera_vez: new Date().toISOString() },
];

export default function Demo({ searchParams }) {
  return (
    <>
      <header className="barra"><a className="logo" href="#"><img src="/logo.svg" alt="Flip PropUp" /></a>
        <nav><a href="#">Buscar</a><a href="#">Mis seguimientos</a><a href="#">Búsquedas guardadas</a><a href="#" aria-current="page">Relevar</a></nav></header>
      <main className="contenido">
        <section id="tarjetas" style={{ display: "grid", gap: 16 }}>
          <div className="encabezado"><div><h2 style={{ margin: 0 }}>1.158 resultados</h2>
            <span className="muted" style={{ fontSize: 14 }}>La Voz: 240 · Mercado Libre: 480 · InmoUP: 50 · CórdobaProp: 388 · Inmobiliarias: 32</span></div>
            <nav className="pestanas"><a href="#" aria-current="page">Lista</a><a href="#">Mapa</a></nav></div>
          <div className="grilla">{EJEMPLOS.map((p) => <Tarjeta key={p.id} p={p} seguido={p.id === 2} />)}</div>
        </section>
        <section id="mapa" style={{ display: "grid", gap: 16 }}>
          <div className="encabezado"><h2 style={{ margin: 0 }}>Vista Mapa</h2>
            <nav className="pestanas"><a href="#">Lista</a><a href="#" aria-current="page">Mapa</a></nav></div>
          <MapaResultados puntos={EJEMPLOS} />
        </section>
        <section id="relevar" style={{ display: "grid", gap: 16 }}>
          <h1>Relevar</h1>
          <p className="muted" style={{ margin: 0 }}>Pasaste por una propiedad interesante: sacale una foto y fijate si está publicada en algún portal.</p>
          <Relevar />
        </section>
      </main>
    </>
  );
}
