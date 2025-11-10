import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PersonForm from './PersonForm';
import type { Person } from '../lib/types';

describe('PersonForm', () => {
  const mockPerson: Person = {
    id: 1,
    name: 'John Doe',
    given: 'John',
    surname: 'Doe',
    birth: '1850',
    death: '1920',
    sex: 'M',
    title: null,
    notes: null,
    gen: 1,
    chart_id: null,
    line_key: null,
    approx: null,
    source_id: 1,
    page_index: 0,
    line_index: 5,
  };

  it('should render the form with person data', () => {
    const onSubmit = vi.fn();
    const onClose = vi.fn();

    render(<PersonForm person={mockPerson} onSubmit={onSubmit} onClose={onClose} />);

    // Check that form inputs are populated
    expect(screen.getByDisplayValue('John Doe')).toBeInTheDocument();
    expect(screen.getByDisplayValue('John')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Doe')).toBeInTheDocument();
    expect(screen.getByDisplayValue('1850')).toBeInTheDocument();
    expect(screen.getByDisplayValue('1920')).toBeInTheDocument();
  });

  it('should display source citation when available', () => {
    const onSubmit = vi.fn();
    const onClose = vi.fn();

    render(<PersonForm person={mockPerson} onSubmit={onSubmit} onClose={onClose} />);

    expect(screen.getByText(/Source Citation:/i)).toBeInTheDocument();
    expect(screen.getByText(/Source ID 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Page 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Line 6/i)).toBeInTheDocument();
  });

  it('should not display source citation when not available', () => {
    const personWithoutSource: Person = {
      ...mockPerson,
      source_id: null,
      page_index: null,
      line_index: null,
    };

    const onSubmit = vi.fn();
    const onClose = vi.fn();

    render(<PersonForm person={personWithoutSource} onSubmit={onSubmit} onClose={onClose} />);

    expect(screen.queryByText(/Source Citation:/i)).not.toBeInTheDocument();
  });

  it('should update form fields when user types', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const onClose = vi.fn();

    render(<PersonForm person={mockPerson} onSubmit={onSubmit} onClose={onClose} />);

    const nameInput = screen.getByDisplayValue('John Doe');

    await user.clear(nameInput);
    await user.type(nameInput, 'Jane Smith');

    expect(nameInput).toHaveValue('Jane Smith');
  });

  it('should call onSubmit with updated data when form is submitted', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const onClose = vi.fn();

    render(<PersonForm person={mockPerson} onSubmit={onSubmit} onClose={onClose} />);

    const nameInput = screen.getByDisplayValue('John Doe');
    const submitButton = screen.getByText(/save/i);

    await user.clear(nameInput);
    await user.type(nameInput, 'Jane Smith');
    await user.click(submitButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledOnce();
    });

    // Verify the payload
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Jane Smith',
        given: 'John',
        surname: 'Doe',
        birth: '1850',
        death: '1920',
        sex: 'M',
      })
    );
  });

  it('should call onClose after successful submission', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onClose = vi.fn();

    render(<PersonForm person={mockPerson} onSubmit={onSubmit} onClose={onClose} />);

    const submitButton = screen.getByText(/save/i);
    await user.click(submitButton);

    await waitFor(() => {
      expect(onClose).toHaveBeenCalledOnce();
    });
  });

  it('should call onClose when cancel button is clicked', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const onClose = vi.fn();

    render(<PersonForm person={mockPerson} onSubmit={onSubmit} onClose={onClose} />);

    const cancelButton = screen.getByText(/cancel/i);
    await user.click(cancelButton);

    expect(onClose).toHaveBeenCalledOnce();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('should disable submit button while saving', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn(() => new Promise((resolve) => setTimeout(resolve, 100)));
    const onClose = vi.fn();

    render(<PersonForm person={mockPerson} onSubmit={onSubmit} onClose={onClose} />);

    const submitButton = screen.getByText(/save/i);

    expect(submitButton).not.toBeDisabled();

    user.click(submitButton);

    // Button should be disabled while saving
    await waitFor(() => {
      expect(submitButton).toBeDisabled();
    });
  });

  it('should handle sex field selection', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const onClose = vi.fn();

    render(<PersonForm person={mockPerson} onSubmit={onSubmit} onClose={onClose} />);

    // Find the sex select by label (now properly associated)
    const sexSelect = screen.getByLabelText(/sex/i);

    await user.selectOptions(sexSelect, 'F');

    expect(sexSelect).toHaveValue('F');
  });

  it('should convert empty string fields to null', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const onClose = vi.fn();

    const personWithNullFields: Person = {
      ...mockPerson,
      title: 'Dr.',
      notes: 'Some notes',
    };

    render(<PersonForm person={personWithNullFields} onSubmit={onSubmit} onClose={onClose} />);

    const titleInput = screen.getByDisplayValue('Dr.');
    const submitButton = screen.getByText(/save/i);

    // Clear the title field
    await user.clear(titleInput);
    await user.click(submitButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          title: null, // Empty string converted to null
        })
      );
    });
  });
});
