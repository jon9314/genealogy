import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Modal from './Modal';

describe('Modal', () => {
  let onClose: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onClose = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render when isOpen is true', () => {
    render(
      <Modal isOpen={true} onClose={onClose}>
        <div>Modal Content</div>
      </Modal>
    );

    expect(screen.getByText('Modal Content')).toBeInTheDocument();
  });

  it('should not render when isOpen is false', () => {
    render(
      <Modal isOpen={false} onClose={onClose}>
        <div>Modal Content</div>
      </Modal>
    );

    expect(screen.queryByText('Modal Content')).not.toBeInTheDocument();
  });

  it('should have proper ARIA attributes', () => {
    render(
      <Modal isOpen={true} onClose={onClose} title="Test Modal">
        <div>Modal Content</div>
      </Modal>
    );

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'modal-title');
  });

  it('should close when Escape key is pressed', async () => {
    const user = userEvent.setup();

    render(
      <Modal isOpen={true} onClose={onClose}>
        <div>Modal Content</div>
      </Modal>
    );

    await user.keyboard('{Escape}');

    expect(onClose).toHaveBeenCalledOnce();
  });

  it('should close when clicking the backdrop', async () => {
    const user = userEvent.setup();

    render(
      <Modal isOpen={true} onClose={onClose}>
        <div>Modal Content</div>
      </Modal>
    );

    const backdrop = screen.getByRole('dialog');
    await user.click(backdrop);

    expect(onClose).toHaveBeenCalledOnce();
  });

  it('should not close when clicking modal content', async () => {
    const user = userEvent.setup();

    render(
      <Modal isOpen={true} onClose={onClose}>
        <div>Modal Content</div>
      </Modal>
    );

    const content = screen.getByText('Modal Content');
    await user.click(content);

    expect(onClose).not.toHaveBeenCalled();
  });

  it('should trap focus within modal', async () => {
    const user = userEvent.setup();

    render(
      <Modal isOpen={true} onClose={onClose}>
        <div>
          <button>First Button</button>
          <button>Second Button</button>
          <button>Third Button</button>
        </div>
      </Modal>
    );

    const firstButton = screen.getByText('First Button');
    const secondButton = screen.getByText('Second Button');
    const thirdButton = screen.getByText('Third Button');

    // Focus first button
    firstButton.focus();
    expect(firstButton).toHaveFocus();

    // Tab to second button
    await user.tab();
    expect(secondButton).toHaveFocus();

    // Tab to third button
    await user.tab();
    expect(thirdButton).toHaveFocus();

    // Tab from last button should wrap to first
    await user.tab();
    expect(firstButton).toHaveFocus();

    // Shift+Tab from first button should wrap to last
    await user.tab({ shift: true });
    expect(thirdButton).toHaveFocus();
  });

  it('should auto-focus first focusable element', () => {
    render(
      <Modal isOpen={true} onClose={onClose}>
        <div>
          <input placeholder="First input" />
          <button>Submit</button>
        </div>
      </Modal>
    );

    const firstInput = screen.getByPlaceholderText('First input');
    expect(firstInput).toHaveFocus();
  });

  it('should restore focus to previously focused element on close', () => {
    const { rerender } = render(
      <div>
        <button>Outside Button</button>
        <Modal isOpen={false} onClose={onClose}>
          <div>Modal Content</div>
        </Modal>
      </div>
    );

    const outsideButton = screen.getByText('Outside Button');
    outsideButton.focus();
    expect(outsideButton).toHaveFocus();

    // Open modal
    rerender(
      <div>
        <button>Outside Button</button>
        <Modal isOpen={true} onClose={onClose}>
          <input placeholder="Modal input" />
        </Modal>
      </div>
    );

    // Focus should move to modal input
    const modalInput = screen.getByPlaceholderText('Modal input');
    expect(modalInput).toHaveFocus();

    // Close modal
    rerender(
      <div>
        <button>Outside Button</button>
        <Modal isOpen={false} onClose={onClose}>
          <input placeholder="Modal input" />
        </Modal>
      </div>
    );

    // Focus should return to outside button
    expect(outsideButton).toHaveFocus();
  });
});
