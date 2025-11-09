import { useEffect, useState } from "react";

import GraphView from "../components/GraphView";
import PersonForm from "../components/PersonForm";
import { useUndoRedo } from "../hooks/useUndoRedo";
import { listFamilies, listPersons, reparent, updatePerson, getRelationshipValidation } from "../lib/api";
import type { FamilyWithChildren, Person, UpdatePersonPayload, RelationshipValidation } from "../lib/types";

export default function GraphPage() {
  const [people, setPeople] = useState<Person[]>([]);
  const [families, setFamilies] = useState<FamilyWithChildren[]>([]);
  const [editing, setEditing] = useState<Person | null>(null);
  const [relationshipData, setRelationshipData] = useState<RelationshipValidation | null>(null);
  const { push } = useUndoRedo();

  useEffect(() => {
    refresh();
  }, []);

  const refresh = async () => {
    const [personsData, familyData, relationshipData] = await Promise.all([
      listPersons(),
      listFamilies(),
      getRelationshipValidation(),
    ]);
    setPeople(personsData);
    setFamilies(familyData);
    setRelationshipData(relationshipData);
  };

  const mapById = useMemo(() => new Map(people.map((person) => [person.id, person])), [people]);

  const handleEdit = async (payload: UpdatePersonPayload) => {
    if (!editing) return;
    const before = editing;
    await push(
      {
        label: `Update ${before.name}`,
        redo: async () => {
          const updated = await updatePerson(before.id, payload);
          setPeople((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
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
          setPeople((prev) => prev.map((item) => (item.id === reverted.id ? reverted : item)));
        },
      },
      true
    );
    setEditing(null);
  };

  const handleReparent = async (childId: number, parentId: number) => {
    const previousFamily = families.find((family) => family.children.some((child) => child.person_id === childId));
    await push(
      {
        label: `Reparent person ${childId}`,
        redo: async () => {
          await reparent({ person_id: childId, new_parent_person_id: parentId });
          await refresh();
        },
        undo: async () => {
          if (!previousFamily) return;
          await reparent({ person_id: childId, new_family_id: previousFamily.id });
          await refresh();
        },
      },
      true
    );
  };

  return (
    <div className="grid" style={{ gap: "1.5rem" }}>
      <div className="card">
        <p>Drag a person toward a new parent (one generation higher). Confirm the reparent action when prompted.</p>
      </div>
      <GraphView
        people={people}
        families={families}
        onEdit={(person) => setEditing(person)}
        onReparent={handleReparent}
        relationshipData={relationshipData}
      />
      {editing && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "grid", placeItems: "center" }}>
          <PersonForm person={editing} onSubmit={handleEdit} onClose={() => setEditing(null)} />
        </div>
      )}
    </div>
  );
}
