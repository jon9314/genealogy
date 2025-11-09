import { useEffect, useMemo, useState } from "react";

import { useUndoRedo } from "../hooks/useUndoRedo";
import { deletePerson, listPersons } from "../lib/api";
import type { Person } from "../lib/types";

interface DuplicateGroup {
  key: string;
  members: Person[];
}

export default function ReviewPage() {
  const [persons, setPersons] = useState<Person[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const { push } = useUndoRedo();

  useEffect(() => {
    listPersons().then(setPersons);
  }, []);

  const duplicates = useMemo<DuplicateGroup[]>(() => {
    const map = new Map<string, Person[]>();
    persons.forEach((person) => {
      const birthYear = person.birth?.match(/\d{4}/)?.[0] ?? "";
      const key = `${(person.surname || "").toLowerCase()}|${(person.given || "").toLowerCase()}|${birthYear}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(person);
    });
    return Array.from(map.entries())
      .filter(([, members]) => members.length > 1)
      .map(([key, members]) => ({ key, members }));
  }, [persons]);

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
          const fresh = await listPersons();
          setPersons(fresh);
        },
      },
      true
    );
  };

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <div className="card">
        <h2>Potential duplicates</h2>
        <p>
          Review potential duplicates grouped by surname, given name, and birth year.
          The parser uses fuzzy matching (±2 year tolerance, phonetic name matching) to reduce duplicates during import.
          Manually resolve any remaining duplicates by editing or deleting extras.
        </p>
      </div>
      {duplicates
        .filter((group) => !dismissed.has(group.key))
        .map((group) => (
          <div key={group.key} className="card">
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <div>
                <div className="badge">Key {group.key}</div>
                <div>{group.members.length} matches</div>
              </div>
              <button className="btn secondary" onClick={() => setDismissed((prev) => new Set(prev).add(group.key))}>
                Mark resolved
              </button>
            </div>
            <div className="grid" style={{ gap: "0.75rem", marginTop: "1rem" }}>
              {group.members.map((member) => (
                <div key={member.id} className="card" style={{ background: "rgba(0,0,0,0.25)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>{member.name}</div>
                      <div style={{ fontSize: "0.85rem", opacity: 0.8 }}>
                        Birth: {member.birth || "?"} � Death: {member.death || "?"}
                      </div>
                    </div>
                    <button className="btn secondary" onClick={() => void handleDelete(member)}>
                      Delete
                    </button>
                  </div>
                  <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", opacity: 0.8 }}>
                    Notes: {member.notes || "�"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      {!duplicates.length && <p>No duplicates detected.</p>}
    </div>
  );
}
