import { describe, it, expect, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { UndoProvider, useUndoRedo } from './useUndoRedo';
import { ReactNode } from 'react';

const wrapper = ({ children }: { children: ReactNode }) => <UndoProvider>{children}</UndoProvider>;

describe('useUndoRedo', () => {
  it('should throw error when used outside UndoProvider', () => {
    // Suppress console.error for this test
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => useUndoRedo());
    }).toThrow('useUndoRedo must be used inside UndoProvider');

    consoleError.mockRestore();
  });

  it('should start with empty history', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(false);
    expect(result.current.history).toEqual([]);
    expect(result.current.currentPosition).toBe(0);
  });

  it('should push an action and execute redo immediately', async () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    const redoFn = vi.fn();
    const undoFn = vi.fn();

    await act(async () => {
      await result.current.push({
        label: 'Test Action',
        redo: redoFn,
        undo: undoFn,
      });
    });

    expect(redoFn).toHaveBeenCalledOnce();
    expect(undoFn).not.toHaveBeenCalled();
    expect(result.current.canUndo).toBe(true);
    expect(result.current.canRedo).toBe(false);
    expect(result.current.history).toHaveLength(1);
    expect(result.current.currentPosition).toBe(1);
  });

  it('should push action without executing when immediate=false', async () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    const redoFn = vi.fn();
    const undoFn = vi.fn();

    await act(async () => {
      await result.current.push(
        {
          label: 'Test Action',
          redo: redoFn,
          undo: undoFn,
        },
        false
      );
    });

    expect(redoFn).not.toHaveBeenCalled();
    expect(undoFn).not.toHaveBeenCalled();
    expect(result.current.canUndo).toBe(true);
  });

  it('should undo an action', async () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    const redoFn = vi.fn();
    const undoFn = vi.fn();

    await act(async () => {
      await result.current.push({
        label: 'Test Action',
        redo: redoFn,
        undo: undoFn,
      });
    });

    await act(async () => {
      await result.current.undo();
    });

    expect(undoFn).toHaveBeenCalledOnce();
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(true);
    expect(result.current.currentPosition).toBe(0);
  });

  it('should redo an action after undo', async () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    const redoFn = vi.fn();
    const undoFn = vi.fn();

    await act(async () => {
      await result.current.push({
        label: 'Test Action',
        redo: redoFn,
        undo: undoFn,
      });
    });

    await act(async () => {
      await result.current.undo();
    });

    // Clear mock calls to verify redo is called again
    redoFn.mockClear();

    await act(async () => {
      await result.current.redo();
    });

    expect(redoFn).toHaveBeenCalledOnce();
    expect(result.current.canUndo).toBe(true);
    expect(result.current.canRedo).toBe(false);
    expect(result.current.currentPosition).toBe(1);
  });

  it('should clear future when pushing new action', async () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    const action1 = { label: 'Action 1', redo: vi.fn(), undo: vi.fn() };
    const action2 = { label: 'Action 2', redo: vi.fn(), undo: vi.fn() };
    const action3 = { label: 'Action 3', redo: vi.fn(), undo: vi.fn() };

    await act(async () => {
      await result.current.push(action1);
      await result.current.push(action2);
    });

    await act(async () => {
      await result.current.undo();
    });

    expect(result.current.canRedo).toBe(true);

    // Push new action should clear future
    await act(async () => {
      await result.current.push(action3);
    });

    expect(result.current.canRedo).toBe(false);
    expect(result.current.history).toHaveLength(2); // action1 and action3, not action2
  });

  it('should save checkpoint', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    act(() => {
      result.current.saveCheckpoint('My Checkpoint');
    });

    expect(result.current.history).toHaveLength(1);
    expect(result.current.history[0].label).toBe('📍 Checkpoint: My Checkpoint');
    expect(result.current.history[0].isCheckpoint).toBe(true);
    expect(result.current.canUndo).toBe(true);
  });

  it('should handle async redo/undo functions', async () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    const redoFn = vi.fn(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
    });
    const undoFn = vi.fn(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    await act(async () => {
      await result.current.push({
        label: 'Async Action',
        redo: redoFn,
        undo: undoFn,
      });
    });

    expect(redoFn).toHaveBeenCalledOnce();

    await act(async () => {
      await result.current.undo();
    });

    await waitFor(() => {
      expect(undoFn).toHaveBeenCalledOnce();
    });
  });

  it('should handle multiple actions in sequence', async () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    const actions = [
      { label: 'Action 1', redo: vi.fn(), undo: vi.fn() },
      { label: 'Action 2', redo: vi.fn(), undo: vi.fn() },
      { label: 'Action 3', redo: vi.fn(), undo: vi.fn() },
    ];

    for (const action of actions) {
      await act(async () => {
        await result.current.push(action);
      });
    }

    expect(result.current.history).toHaveLength(3);
    expect(result.current.currentPosition).toBe(3);

    // Undo all - need to await each one separately
    await act(async () => {
      await result.current.undo();
    });

    await act(async () => {
      await result.current.undo();
    });

    await act(async () => {
      await result.current.undo();
    });

    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(true);

    // Verify undo functions called in reverse order
    expect(actions[2].undo).toHaveBeenCalled();
    expect(actions[1].undo).toHaveBeenCalled();
    expect(actions[0].undo).toHaveBeenCalled();
  });

  it('should not crash when undoing with empty history', async () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    await act(async () => {
      await result.current.undo();
    });

    expect(result.current.canUndo).toBe(false);
  });

  it('should not crash when redoing with empty future', async () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    await act(async () => {
      await result.current.redo();
    });

    expect(result.current.canRedo).toBe(false);
  });
});
