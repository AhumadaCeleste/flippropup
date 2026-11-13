// Se muestra al instante al cambiar de página mientras llegan los datos.
export default function Cargando() {
  return (
    <div className="panel vacio" aria-busy="true" style={{ opacity: 0.8 }}>
      <h2 style={{ margin: 0 }}>Cargando…</h2>
    </div>
  );
}
