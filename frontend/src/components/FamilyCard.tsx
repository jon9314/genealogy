import type { FamilyWithChildren, Person } from "../lib/types";

interface Props {
  family: FamilyWithChildren;
  peopleById: Map<number, Person>;
}

export default function FamilyCard({ family, peopleById }: Props) {
  const husband = family.husband_id ? peopleById.get(family.husband_id) : null;
  const wife = family.wife_id ? peopleById.get(family.wife_id) : null;
  return (
    <div className="card">
      <div style={{ fontWeight: 600, marginBottom: "0.5rem" }}>Family #{family.id}</div>
      <div className="grid" style={{ gap: "0.5rem" }}>
        <div>
          <div className="badge">Husband</div>
          <div>{husband ? husband.name : "—"}</div>
        </div>
        <div>
          <div className="badge">Wife</div>
          <div>{wife ? wife.name : "—"}</div>
        </div>
      </div>
      <div style={{ marginTop: "0.75rem" }}>
        <div className="badge">Children</div>
        <ol style={{ paddingLeft: "1.25rem", marginTop: "0.5rem" }}>
          {family.children.map((child) => {
            const person = peopleById.get(child.person_id);
            return <li key={child.id}>{person ? person.name : `Person ${child.person_id}`}</li>;
          })}
        </ol>
      </div>
    </div>
  );
}
