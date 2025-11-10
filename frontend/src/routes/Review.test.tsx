import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import Review from './Review';
import { UndoProvider } from '../hooks/useUndoRedo';
import type { Person } from '../lib/types';

// Mock API functions
const mockListPersons = vi.fn();
const mockDeletePerson = vi.fn();
const mockBulkDeletePersons = vi.fn();

vi.mock('../lib/api', () => ({
  listPersons: () => mockListPersons(),
  deletePerson: (...args: any[]) => mockDeletePerson(...args),
  bulkDeletePersons: (...args: any[]) => mockBulkDeletePersons(...args),
}));

// Mock confirm
global.confirm = vi.fn(() => true);

const mockPersons: Person[] = [
  // Duplicate group 1: John Doe, 1850
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
    name: 'John Doe',
    given: 'John',
    surname: 'Doe',
    birth: '1850',
    death: '1920',
    sex: 'M',
    gen: 1,
    source_id: 2,
    source_line: 1,
    source_page: 1,
    line_key: 'key2',
    chart_id: null,
    title: null,
    notes: null,
    birth_approx: false,
    death_approx: false,
  },
  {
    id: 3,
    name: 'John Doe',
    given: 'John',
    surname: 'Doe',
    birth: '1850',
    death: '1920',
    sex: 'M',
    gen: 1,
    source_id: 3,
    source_line: 1,
    source_page: 1,
    line_key: 'key3',
    chart_id: null,
    title: null,
    notes: null,
    birth_approx: false,
    death_approx: false,
  },
  // Duplicate group 2: Jane Smith, 1875
  {
    id: 4,
    name: 'Jane Smith',
    given: 'Jane',
    surname: 'Smith',
    birth: '1875',
    death: '1945',
    sex: 'F',
    gen: 2,
    source_id: 1,
    source_line: 2,
    source_page: 1,
    line_key: 'key4',
    chart_id: null,
    title: null,
    notes: null,
    birth_approx: false,
    death_approx: false,
  },
  {
    id: 5,
    name: 'Jane Smith',
    given: 'Jane',
    surname: 'Smith',
    birth: '1875',
    death: '1945',
    sex: 'F',
    gen: 2,
    source_id: 2,
    source_line: 1,
    source_page: 1,
    line_key: 'key5',
    chart_id: null,
    title: null,
    notes: null,
    birth_approx: false,
    death_approx: false,
  },
  // Unique person
  {
    id: 6,
    name: 'Bob Unique',
    given: 'Bob',
    surname: 'Unique',
    birth: '1900',
    death: '1980',
    sex: 'M',
    gen: 3,
    source_id: 1,
    source_line: 3,
    source_page: 1,
    line_key: 'key6',
    chart_id: null,
    title: null,
    notes: null,
    birth_approx: false,
    death_approx: false,
  },
];

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <UndoProvider>{children}</UndoProvider>
  </BrowserRouter>
);

describe('Review', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListPersons.mockResolvedValue(mockPersons);
  });

  it('should render duplicate groups', async () => {
    render(<Review />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getAllByText(/John Doe/)).toHaveLength(3);
    });

    // Should show both duplicate groups
    expect(screen.getAllByText(/Jane Smith/)).toHaveLength(2);

    // Should not show unique person (no duplicates)
    expect(screen.queryByText(/Bob Unique/)).not.toBeInTheDocument();
  });

  it('should show correct duplicate count', async () => {
    render(<Review />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getAllByText(/John Doe/)).toHaveLength(3);
    });

    // Should show "3 matches" for John Doe group
    expect(screen.getByText(/3 matches/i)).toBeInTheDocument();

    // Should show "2 matches" for Jane Smith group
    expect(screen.getByText(/2 matches/i)).toBeInTheDocument();
  });

  it('should show confirm dialog when deleting individual person', async () => {
    const user = userEvent.setup();
    render(<Review />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getAllByText(/John Doe/)).toHaveLength(3);
    });

    // Find and click first delete button
    const deleteButtons = screen.getAllByText(/^Delete$/);
    await user.click(deleteButtons[0]);

    // Should call confirm
    expect(global.confirm).toHaveBeenCalledWith(expect.stringContaining('Delete John Doe'));
  });

  it('should show confirm dialog when resolving duplicate group', async () => {
    const user = userEvent.setup();
    render(<Review />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getAllByText(/John Doe/)).toHaveLength(3);
    });

    // Find and click auto-resolve button
    const resolveButtons = screen.getAllByText(/Auto-Resolve \(keep first\)/i);
    await user.click(resolveButtons[0]);

    // Should call confirm with keep/delete message
    expect(global.confirm).toHaveBeenCalledWith(
      expect.stringMatching(/Keep.*delete.*duplicate/)
    );
  });

  it('should call bulkDeletePersons when resolving group', async () => {
    const user = userEvent.setup();
    mockBulkDeletePersons.mockResolvedValue(undefined);

    render(<Review />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getAllByText(/John Doe/)).toHaveLength(3);
    });

    // Click auto-resolve button for John Doe group
    const resolveButtons = screen.getAllByText(/Auto-Resolve \(keep first\)/i);
    await user.click(resolveButtons[0]);

    // Should call bulkDeletePersons with correct IDs
    await waitFor(() => {
      expect(mockBulkDeletePersons).toHaveBeenCalledWith(
        expect.arrayContaining([2, 3]), // Delete IDs
        1 // Keep ID
      );
    });
  });

  it('should mark a duplicate group as resolved', async () => {
    const user = userEvent.setup();
    render(<Review />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getAllByText(/John Doe/)).toHaveLength(3);
    });

    // Click mark resolved button
    const markResolvedButtons = screen.getAllByText(/Mark resolved/i);
    await user.click(markResolvedButtons[0]);

    // John Doe group should no longer be visible
    expect(screen.queryByText(/John Doe/)).not.toBeInTheDocument();

    // Jane Smith group should still be visible
    expect(screen.getAllByText(/Jane Smith/)).toHaveLength(2);
  });

  it('should show message when no duplicates found', async () => {
    // Mock with only unique persons
    mockListPersons.mockResolvedValue([mockPersons[5]]);

    render(<Review />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText(/no duplicates detected/i)).toBeInTheDocument();
    });
  });

  it('should group by surname, given name, and birth year', async () => {
    // Test that persons with different birth years are not grouped
    const differentYear: Person[] = [
      mockPersons[0], // John Doe 1850
      {
        ...mockPersons[1],
        id: 99,
        birth: '1851', // Different year
      },
    ];

    mockListPersons.mockResolvedValue(differentYear);

    render(<Review />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      // Should not show any duplicate groups (different birth years)
      expect(screen.getByText(/no duplicates detected/i)).toBeInTheDocument();
    });
  });
});
