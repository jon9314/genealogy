import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import GraphView from './GraphView';
import type { Person, FamilyWithChildren } from '../lib/types';

// Mock ReactFlow to avoid canvas rendering issues in tests
vi.mock('reactflow', () => ({
  __esModule: true,
  default: ({ children }: any) => <div data-testid="react-flow">{children}</div>,
  Background: () => <div data-testid="background" />,
  Controls: () => <div data-testid="controls" />,
  MiniMap: () => <div data-testid="minimap" />,
  ReactFlowProvider: ({ children }: any) => <div>{children}</div>,
}));

const mockPeople: Person[] = [
  {
    id: 1,
    name: 'John Doe',
    given: 'John',
    surname: 'Doe',
    birth: '1850',
    death: '1920',
    sex: 'M',
    gen: 1,
    source_id: 1,
    source_line: 1,
    source_page: 1,
    line_key: 'key1',
    chart_id: null,
    title: null,
    notes: null,
    birth_approx: false,
    death_approx: false,
  },
  {
    id: 2,
    name: 'Jane Doe',
    given: 'Jane',
    surname: 'Doe',
    birth: '1875',
    death: '1945',
    sex: 'F',
    gen: 2,
    source_id: 1,
    source_line: 2,
    source_page: 1,
    line_key: 'key2',
    chart_id: null,
    title: null,
    notes: null,
    birth_approx: false,
    death_approx: false,
  },
];

const mockFamilies: FamilyWithChildren[] = [
  {
    id: 1,
    source_id: 1,
    husband_id: 1,
    wife_id: null,
    children: [
      {
        id: 1,
        family_id: 1,
        person_id: 2,
        child_order: 1,
      },
    ],
  },
];

describe('GraphView', () => {
  it('should render without crashing', () => {
    const onEdit = vi.fn();
    const onReparent = vi.fn();

    render(
      <GraphView
        people={mockPeople}
        families={mockFamilies}
        onEdit={onEdit}
        onReparent={onReparent}
        relationshipData={null}
      />
    );

    // Should render the ReactFlow component
    expect(screen.getByTestId('react-flow')).toBeInTheDocument();
  });

  it('should render controls and background', () => {
    const onEdit = vi.fn();
    const onReparent = vi.fn();

    render(
      <GraphView
        people={mockPeople}
        families={mockFamilies}
        onEdit={onEdit}
        onReparent={onReparent}
        relationshipData={null}
      />
    );

    expect(screen.getByTestId('controls')).toBeInTheDocument();
    expect(screen.getByTestId('background')).toBeInTheDocument();
    expect(screen.getByTestId('minimap')).toBeInTheDocument();
  });

  it('should handle empty data', () => {
    const onEdit = vi.fn();
    const onReparent = vi.fn();

    render(
      <GraphView
        people={[]}
        families={[]}
        onEdit={onEdit}
        onReparent={onReparent}
        relationshipData={null}
      />
    );

    // Should still render the flow component
    expect(screen.getByTestId('react-flow')).toBeInTheDocument();
  });
});
