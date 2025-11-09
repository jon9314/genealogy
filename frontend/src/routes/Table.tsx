import { useEffect, useMemo, useState } from "react";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  useReactTable,
} from "@tanstack/react-table";

import PersonForm from "../components/PersonForm";
import { useUndoRedo } from "../hooks/useUndoRedo";
import { bulkUpdatePersons, deletePerson, listPersons, listSources, updatePerson } from "../lib/api";
import type { Person, Source, UpdatePersonPayload } from "../lib/types";

export default function TablePage() {
  const [persons, setPersons] = useState<Person[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [filters, setFilters] = useState({ gen: "", surname: "", sourceId: "", search: "" });
  const [editing, setEditing] = useState<Person | null>(null);
  const [bulkEditMode, setBulkEditMode] = useState(false);
  const [bulkEditField, setBulkEditField] = useState<"sex" | "surname">("sex");
  const [bulkEditValue, setBulkEditValue] = useState("");
  const { push } = useUndoRedo();

  useEffect(() => {
    refresh();
  }, []);

  const refresh = async () => {
    const [peopleData, sourcesData] = await Promise.all([listPersons(), listSources()]);
    setPersons(peopleData);
    setSources(sourcesData);
  };

  const filtered = useMemo(() => {
    return persons.filter((person) => {
      if (filters.gen && String(person.gen) !== filters.gen) return false;
      if (filters.surname && !(person.surname || "").toLowerCase().includes(filters.surname.toLowerCase())) return false;
      if (filters.sourceId && String(person.source_id ?? "") !== filters.sourceId) return false;
      if (filters.search) {
        const target = `${person.name} ${person.notes ?? ""}`.toLowerCase();
        if (!target.includes(filters.search.toLowerCase())) return false;
      }
      return true;
    });
  }, [filters, persons]);

  const columns = useMemo<ColumnDef<Person>[]>(
    () => [
      { header: "ID", accessorKey: "id" },
      { header: "Gen", accessorKey: "gen" },
      { header: "Name", accessorKey: "name" },
      { header: "Birth", accessorKey: "birth" },
      { header: "Death", accessorKey: "death" },
      { header: "Surname", accessorKey: "surname" },
      { header: "Source", accessorFn: (row) => sources.find((s) => s.id === row.source_id)?.name ?? "�" },
    ],
    [sources]
  );

  const table = useReactTable({
    columns,
    data: filtered,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  const handleUpdate = async (payload: UpdatePersonPayload) => {
    if (!editing) return;
    const before = editing;
    await push(
      {
        label: `Update ${before.name}`,
        redo: async () => {
          const updated = await updatePerson(before.id, payload);
          setPersons((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
        },
        undo: async () => {
          const reverted = await updatePerson(before.id, {
            name: before.name,
            given: before.given,
            surname: before.surname,
            birth: before.birth,
            death: before.death,
            title: before.title,
            notes: before.notes,
            sex: before.sex,
            chart_id: before.chart_id,
          });
          setPersons((prev) => prev.map((item) => (item.id === reverted.id ? reverted : item)));
        },
      },
      true
    );
    setEditing(null);
  };

  const handleDelete = async (person: Person) => {
    if (!window.confirm(`Delete ${person.name}?`)) return;
    await push(
      {
        label: `Delete ${person.name}`,
        redo: async () => {
          await deletePerson(person.id);
          setPersons((prev) => prev.filter((item) => item.id !== person.id));
        },
        undo: async () => {
          await refresh();
        },
      },
      true
    );
  };

  const handleBulkEdit = async () => {
    if (!bulkEditValue.trim()) {
      window.alert("Please enter a value to set");
      return;
    }

    if (filtered.length === 0) {
      window.alert("No people match the current filters");
      return;
    }

    const personIds = filtered.map((p) => p.id);
    const updates = { [bulkEditField]: bulkEditValue };

    const confirmMsg = `Set ${bulkEditField} to "${bulkEditValue}" for ${personIds.length} ${personIds.length === 1 ? "person" : "people"}?`;
    if (!window.confirm(confirmMsg)) return;

    await push(
      {
        label: `Bulk edit ${bulkEditField} for ${personIds.length} people`,
        redo: async () => {
          await bulkUpdatePersons(personIds, updates);
          await refresh();
        },
        undo: async () => {
          await refresh();
        },
      },
      true
    );

    // Reset bulk edit state
    setBulkEditMode(false);
    setBulkEditValue("");
  };

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <div className="card" style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <label>Generation</label>
          <input value={filters.gen} onChange={(e) => setFilters((prev) => ({ ...prev, gen: e.target.value }))} placeholder="1" />
        </div>
        <div>
          <label>Surname</label>
          <input value={filters.surname} onChange={(e) => setFilters((prev) => ({ ...prev, surname: e.target.value }))} placeholder="NEWCOMB" />
        </div>
        <div>
          <label>Source</label>
          <select value={filters.sourceId} onChange={(e) => setFilters((prev) => ({ ...prev, sourceId: e.target.value }))}>
            <option value="">All</option>
            {sources.map((source) => (
              <option key={source.id} value={source.id}>
                {source.name}
              </option>
            ))}
          </select>
        </div>
        <div style={{ flex: 1 }}>
          <label>Search</label>
          <input value={filters.search} onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))} placeholder="Name or notes" />
        </div>
      </div>

      {/* Bulk Edit Section */}
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
          <button
            className={`btn ${bulkEditMode ? "" : "secondary"}`}
            onClick={() => setBulkEditMode(!bulkEditMode)}
          >
            {bulkEditMode ? "Exit Bulk Edit" : "Bulk Edit Mode"}
          </button>

          {bulkEditMode && (
            <>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flex: 1 }}>
                <span>Set</span>
                <select
                  value={bulkEditField}
                  onChange={(e) => setBulkEditField(e.target.value as "sex" | "surname")}
                  style={{ padding: "0.5rem" }}
                >
                  <option value="sex">Sex</option>
                  <option value="surname">Surname</option>
                </select>
                <span>to</span>
                <input
                  type="text"
                  value={bulkEditValue}
                  onChange={(e) => setBulkEditValue(e.target.value)}
                  placeholder={bulkEditField === "sex" ? "M or F" : "SURNAME"}
                  style={{ flex: 1, maxWidth: "200px" }}
                />
                <span style={{ opacity: 0.7 }}>for {filtered.length} {filtered.length === 1 ? "person" : "people"}</span>
              </div>
              <button className="btn" onClick={handleBulkEdit} disabled={!bulkEditValue.trim()}>
                Apply to {filtered.length}
              </button>
            </>
          )}
        </div>
      </div>

      <div className="table-wrapper">
        <table className="table">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th key={header.id}>{flexRender(header.column.columnDef.header, header.getContext())}</th>
                ))}
                <th>Actions</th>
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>
                    {flexRender(cell.column.columnDef.cell ?? ((ctx) => ctx.getValue()), cell.getContext())}
                  </td>
                ))}
                <td>
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <button className="btn secondary" onClick={() => setEditing(row.original)}>
                      Edit
                    </button>
                    <button className="btn secondary" onClick={() => void handleDelete(row.original)}>
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editing && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "grid", placeItems: "center" }}>
          <PersonForm person={editing} onSubmit={handleUpdate} onClose={() => setEditing(null)} />
        </div>
      )}
    </div>
  );
}
