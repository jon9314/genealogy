import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import Table from './Table';
import { UndoProvider } from '../hooks/useUndoRedo';
import type { Person, Source } from '../lib/types';

// Mock API functions
const mockListPersons = vi.fn();
const mockListSources = vi.fn();
const mockUpdatePerson = vi.fn();
const mockDeletePerson = vi.fn();
const mockBulkUpdatePersons = vi.fn();

vi.mock('../lib/api', () => ({
  listPersons: () => mockListPersons(),
  listSources: () => mockListSources(),
  updatePerson: (...args: any[]) => mockUpdatePerson(...args),
  deletePerson: (...args: any[]) => mockDeletePerson(...args),
  bulkUpdatePersons: (...args: any[]) => mockBulkUpdatePersons(...args),
}));

// Mock confirm and alert
global.confirm = vi.fn(() => true);
global.alert = vi.fn();

const mockPersons: Person[] = [
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
    line_key: 'key2',
    chart_id: null,
    title: null,
    notes: null,
    birth_approx: false,
    death_approx: false,
  },
  {
    id: 3,
    name: 'Bob Doe',
    given: 'Bob',
    surname: 'Doe',
    birth: '1900',
    death: '1980',
    sex: 'M',
    gen: 3,
    source_id: 2,
    source_line: 1,
    source_page: 1,
    line_key: 'key3',
    chart_id: null,
    title: null,
    notes: 'Important note',
    birth_approx: false,
    death_approx: false,
  },
];

const mockSources: Source[] = [
  { id: 1, name: 'Source 1', path: '/path/1', stage: 'parsed' },
  { id: 2, name: 'Source 2', path: '/path/2', stage: 'parsed' },
];

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <UndoProvider>{children}</UndoProvider>
  </BrowserRouter>
);

describe('Table', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListPersons.mockResolvedValue(mockPersons);
    mockListSources.mockResolvedValue(mockSources);
  });

  it('should render table with person data', async () => {
    render(<Table />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    expect(screen.getByText('Bob Doe')).toBeInTheDocument();
  });

  it('should filter by generation', async () => {
    const user = userEvent.setup();
    render(<Table />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    // Find and fill generation filter
    const genInput = screen.getByPlaceholderText('1');
    await user.type(genInput, '1');

    // Only generation 1 person should be visible
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.queryByText('Jane Smith')).not.toBeInTheDocument();
    expect(screen.queryByText('Bob Doe')).not.toBeInTheDocument();
  });

  it('should filter by surname', async () => {
    const user = userEvent.setup();
    render(<Table />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    // Find and fill surname filter
    const surnameInput = screen.getByPlaceholderText('NEWCOMB');
    await user.type(surnameInput, 'Doe');

    // Only Doe surname persons should be visible
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Bob Doe')).toBeInTheDocument();
    expect(screen.queryByText('Jane Smith')).not.toBeInTheDocument();
  });

  it('should filter by search text', async () => {
    const user = userEvent.setup();
    render(<Table />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    // Find and fill search filter
    const searchInput = screen.getByPlaceholderText('Name or notes');
    await user.type(searchInput, 'Important');

    // Only person with "Important" in notes should be visible
    expect(screen.getByText('Bob Doe')).toBeInTheDocument();
    expect(screen.queryByText('John Doe')).not.toBeInTheDocument();
    expect(screen.queryByText('Jane Smith')).not.toBeInTheDocument();
  });

  it('should filter by source', async () => {
    const user = userEvent.setup();
    render(<Table />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    // Find source select by label (now properly associated)
    const sourceSelect = screen.getByLabelText(/source/i);
    await user.selectOptions(sourceSelect, '1');

    // Only persons from source 1 should be visible
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    expect(screen.queryByText('Bob Doe')).not.toBeInTheDocument();
  });

  it('should toggle bulk edit mode', async () => {
    const user = userEvent.setup();
    render(<Table />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    // Click bulk edit button
    const bulkEditButton = screen.getByText(/bulk edit mode/i);
    await user.click(bulkEditButton);

    // Should show exit bulk edit button
    expect(screen.getByText(/exit bulk edit/i)).toBeInTheDocument();

    // Should show bulk edit controls
    expect(screen.getByText('Set')).toBeInTheDocument();
  });

  it('should show confirm dialog when deleting', async () => {
    const user = userEvent.setup();
    render(<Table />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    // Find and click first delete button
    const deleteButtons = screen.getAllByText(/^Delete$/);
    await user.click(deleteButtons[0]);

    // Should call confirm
    expect(global.confirm).toHaveBeenCalledWith(expect.stringContaining('Delete John Doe'));
  });

  it('should call API when editing a person', async () => {
    const user = userEvent.setup();
    mockUpdatePerson.mockResolvedValue({ ...mockPersons[0], name: 'Updated Name' });

    render(<Table />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    // Find and click edit button
    const editButtons = screen.getAllByText(/^Edit$/);
    await user.click(editButtons[0]);

    // Should open PersonForm modal
    await waitFor(() => {
      expect(screen.getByDisplayValue('John Doe')).toBeInTheDocument();
    });

    // Update the name
    const nameInput = screen.getByDisplayValue('John Doe');
    await user.clear(nameInput);
    await user.type(nameInput, 'Updated Name');

    // Submit form
    const saveButton = screen.getByText(/save/i);
    await user.click(saveButton);

    // Should call updatePerson API
    await waitFor(() => {
      expect(mockUpdatePerson).toHaveBeenCalled();
    });
  });

  it('should display correct number of filtered results', async () => {
    const user = userEvent.setup();
    render(<Table />, { wrapper });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    // Initially should show all 3 persons
    const rows = screen.getAllByRole('row');
    // 1 header row + 3 data rows = 4 total
    expect(rows).toHaveLength(4);

    // Filter by generation 1
    const genInput = screen.getByPlaceholderText('1');
    await user.type(genInput, '1');

    // Should show only 1 data row
    await waitFor(() => {
      const filteredRows = screen.getAllByRole('row');
      // 1 header row + 1 data row = 2 total
      expect(filteredRows).toHaveLength(2);
    });
  });
});
