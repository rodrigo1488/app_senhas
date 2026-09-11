"use client";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export type DashboardFiltersState = {
  from: string;
  to: string;
  setor_id: string;
  operador_id: string;
};

type Props = {
  value: DashboardFiltersState;
  onChange: (next: DashboardFiltersState) => void;
  onApply: () => void;
  setores: { id: number; nome: string }[];
  operadores: { id: number; nome: string; setor_id: number | null }[];
};

const selectClass =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function DashboardFilters({
  value,
  onChange,
  onApply,
  setores,
  operadores,
}: Props) {
  const ops = value.setor_id
    ? operadores.filter((o) => String(o.setor_id) === value.setor_id)
    : operadores;

  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-card p-4 md:flex-row md:flex-wrap md:items-end">
      <div className="grid gap-1.5">
        <Label htmlFor="from">De</Label>
        <Input
          id="from"
          type="date"
          value={value.from}
          onChange={(e) => onChange({ ...value, from: e.target.value })}
          className="w-[160px]"
        />
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="to">Até</Label>
        <Input
          id="to"
          type="date"
          value={value.to}
          onChange={(e) => onChange({ ...value, to: e.target.value })}
          className="w-[160px]"
        />
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="setor">Setor</Label>
        <select
          id="setor"
          className={selectClass}
          value={value.setor_id}
          onChange={(e) =>
            onChange({ ...value, setor_id: e.target.value, operador_id: "" })
          }
        >
          <option value="">Todos</option>
          {setores.map((s) => (
            <option key={s.id} value={s.id}>
              {s.nome}
            </option>
          ))}
        </select>
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="operador">Atendente</Label>
        <select
          id="operador"
          className={selectClass}
          value={value.operador_id}
          onChange={(e) => onChange({ ...value, operador_id: e.target.value })}
        >
          <option value="">Todos</option>
          {ops.map((o) => (
            <option key={o.id} value={o.id}>
              {o.nome}
            </option>
          ))}
        </select>
      </div>
      <Button type="button" onClick={onApply}>
        Aplicar
      </Button>
    </div>
  );
}
