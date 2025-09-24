import { memo, useCallback, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  Edge,
  MiniMap,\n  Node,\n  NodeProps,\n  ReactFlowInstance,
} from "reactflow";

import "reactflow/dist/style.css";
import type { FamilyWithChildren, Person } from "../lib/types";

interface GraphViewProps {
  people: Person[];
  families: FamilyWithChildren[];
  onEdit: (person: Person) => void;
  onReparent: (childId: number, newParentId: number) => Promise<void> | void;
  onAddSpouse?: (person: Person) => void;
}

interface PersonNodeData {
  person: Person;
  onEdit: (person: Person) => void;
  onAddSpouse?: (person: Person) => void;
}

const PersonNode = memo(({ data }: NodeProps<PersonNodeData>) => {
  const { person, onEdit, onAddSpouse } = data;
  return (
    <div
      style={{
        padding: "0.75rem 1rem",
        borderRadius: "12px",
        border: "1px solid rgba(255,255,255,0.1)",
        background: "rgba(15, 23, 42, 0.85)",
        minWidth: "220px",
      }}
    >
      <div style={{ fontWeight: 700 }}>{person.name}</div>
      <div style={{ fontSize: "0.8rem", opacity: 0.75 }}>Gen {person.gen}</div>
      <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
        <button className="btn secondary" onClick={() => onEdit(person)}>
          Edit
        </button>
        {onAddSpouse && (
          <button className="btn secondary" onClick={() => onAddSpouse(person)}>
            Add spouse
          </button>
        )}
      </div>
    </div>
  );
});

const nodeTypes = { person: PersonNode };

export default function GraphView({ people, families, onEdit, onReparent, onAddSpouse }: GraphViewProps) {
  const [instance, setInstance] = useState<ReactFlowInstance>();

  const nodes = useMemo<Node<PersonNodeData>[]>(() => {
    const groups = new Map<number, Person[]>();
    for (const person of people) {
      if (!groups.has(person.gen)) groups.set(person.gen, []);
      groups.get(person.gen)!.push(person);
    }
    const sortedGenerations = Array.from(groups.keys()).sort((a, b) => a - b);
    const results: Node<PersonNodeData>[] = [];
    for (const gen of sortedGenerations) {
      const persons = groups.get(gen)!;
      persons.sort((a, b) => (a.surname || a.name).localeCompare(b.surname || b.name));
      const spacingX = 260;
      const y = (gen - 1) * 180;
      persons.forEach((person, index) => {
        results.push({
          id: `person-${person.id}`,
          type: "person",
          position: { x: index * spacingX, y },
          data: { person, onEdit, onAddSpouse },
        });
      });
    }
    return results;
  }, [onAddSpouse, onEdit, people]);

  const edges = useMemo<Edge[]>(() => {
    const list: Edge[] = [];
    for (const family of families) {
      if (family.husband_id && family.wife_id) {
        list.push({
          id: `fam-${family.id}-spouse`,
          source: `person-${family.husband_id}`,
          target: `person-${family.wife_id}`,
          type: "smoothstep",
          animated: false,
          style: { stroke: "#7fb5ff" },
        });
      }
      const parentId = family.husband_id ?? family.wife_id;
      if (!parentId) continue;
      for (const child of family.children) {
        list.push({
          id: `fam-${family.id}-child-${child.person_id}`,
          source: `person-${parentId}`,
          target: `person-${child.person_id}`,
          type: "step",
          style: { stroke: "#8892b0" },
        });
      }
    }
    return list;
  }, [families]);

  const handleInit = useCallback((flow: ReactFlowInstance) => {
    setInstance(flow);
    flow.fitView({ padding: 0.2 });
  }, []);

  const handleNodeDragStop = useCallback(
    async (_event: any, node: Node<PersonNodeData>) => {
      if (!instance) return;
      const movedPerson = node.data.person;
      const candidates = instance
        .getNodes()
        .filter((other) => other.id !== node.id)
        .filter((other) => {
          const otherPerson: Person = (other.data as PersonNodeData).person;
          return otherPerson.gen === movedPerson.gen - 1;
        });
      if (!candidates.length) return;
      const nearest = candidates.reduce<{ node: Node; distance: number } | null>((acc, current) => {
        const dx = current.position.x - node.position.x;
        const dy = current.position.y - node.position.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (!acc || distance < acc.distance) return { node: current, distance };
        return acc;
      }, null);
      if (!nearest || nearest.distance > 180) return;
      const parent = (nearest.node.data as PersonNodeData).person;
      if (parent.id === movedPerson.id) return;
      const confirmed = window.confirm(`Reparent ${movedPerson.name} under ${parent.name}?`);
      if (!confirmed) return;
      await onReparent(movedPerson.id, parent.id);
    },
    [instance, onReparent]
  );

  return (
    <div style={{ width: "100%", height: "70vh" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onInit={handleInit}
        onNodeDragStop={handleNodeDragStop}
        fitView
      >
        <Background gap={24} color="rgba(255,255,255,0.05)" />
        <Controls />
        <MiniMap pannable zoomable />
      </ReactFlow>
    </div>
  );
}


