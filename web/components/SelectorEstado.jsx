"use client";
import { useTransition } from "react";
import { cambiarEstado } from "@/app/acciones";
import { ESTADOS } from "@/lib/filtros";

export default function SelectorEstado({ id, estado }) {
  const [pendiente, iniciar] = useTransition();
  return (
    <select
      defaultValue={estado}
      disabled={pendiente}
      aria-label="Estado del seguimiento"
      onChange={(e) => iniciar(() => cambiarEstado(id, e.target.value))}
      style={{ minWidth: 140 }}
    >
      {ESTADOS.map((s) => <option key={s} value={s}>{s}</option>)}
    </select>
  );
}
