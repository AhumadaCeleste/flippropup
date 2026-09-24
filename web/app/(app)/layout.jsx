import Link from "next/link";
import { redirect } from "next/navigation";
import { supabaseServidor } from "@/lib/supabase/server";
import { salir } from "@/app/acciones";
import Navegacion from "@/components/Navegacion";

export const dynamic = "force-dynamic";

export default async function LayoutApp({ children }) {
  const supabase = await supabaseServidor();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  const { data: habilitado } = await supabase.rpc("es_habilitado");

  return (
    <>
      <header className="barra">
        <Link href="/buscar" className="logo" aria-label="Flip PropUp, inicio">
          <img src="/logo.svg" alt="Flip PropUp" />
        </Link>
        <Navegacion />
        <div className="usuario">
          <span>{user.email}</span>
          <form action={salir}><button className="btn btn-chico">Salir</button></form>
        </div>
      </header>
      <main className="contenido">
        {habilitado ? children : (
          <div className="panel vacio">
            <h1>No tenés acceso</h1>
            <p>El email {user.email} no está en la lista de usuarios habilitados. Pedile a Cele que lo agregue.</p>
          </div>
        )}
      </main>
    </>
  );
}
