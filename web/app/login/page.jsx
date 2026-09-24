import BotonGoogle from "./BotonGoogle";

export const metadata = { title: "Entrar · Flip PropUp" };

export default async function Login({ searchParams }) {
  const { error } = await searchParams;
  return (
    <main className="login">
      <div className="caja">
        <img src="/logo.svg" alt="Flip PropUp" />
        <p className="muted">Detectá propiedades subvaluadas antes que el mercado.</p>
        <BotonGoogle />
        {error && (
          <p className="error">
            No pudimos iniciar sesión. Si tu email no está habilitado, pedile acceso a Cele.
          </p>
        )}
        <p className="muted" style={{ fontSize: 13 }}>Acceso solo para usuarios habilitados.</p>
      </div>
    </main>
  );
}
