import { createContext, ReactNode, useCallback, useContext, useMemo, useState } from "react";

type UndoAction = {
  label: string;
  redo: () => Promise<void> | void;
  undo: () => Promise<void> | void;
  isCheckpoint?: boolean;
};

type UndoContextValue = {
  canUndo: boolean;
  canRedo: boolean;
  undo: () => Promise<void>;
  redo: () => Promise<void>;
  push: (action: UndoAction, immediate?: boolean) => Promise<void>;
  saveCheckpoint: (label: string) => void;
  history: UndoAction[];
  currentPosition: number;
};

const UndoContext = createContext<UndoContextValue | null>(null);

export function UndoProvider({ children }: { children: ReactNode }) {
  const [past, setPast] = useState<UndoAction[]>([]);
  const [future, setFuture] = useState<UndoAction[]>([]);

  const undo = useCallback(async () => {
    const action = past[past.length - 1];
    if (!action) return;
    await action.undo();
    setPast((prev) => prev.slice(0, -1));
    setFuture((prev) => [action, ...prev]);
  }, [past]);

  const redo = useCallback(async () => {
    const [action, ...rest] = future;
    if (!action) return;
    await action.redo();
    setFuture(rest);
    setPast((prev) => [...prev, action]);
  }, [future]);

  const push = useCallback(async (action: UndoAction, immediate = true) => {
    setPast((prev) => [...prev, action]);
    setFuture([]);
    if (immediate) {
      await action.redo();
    }
  }, []);

  const saveCheckpoint = useCallback((label: string) => {
    const checkpoint: UndoAction = {
      label: `📍 Checkpoint: ${label}`,
      redo: () => {},
      undo: () => {},
      isCheckpoint: true,
    };
    setPast((prev) => [...prev, checkpoint]);
    setFuture([]);
  }, []);

  const value = useMemo<UndoContextValue>(
    () => ({
      canUndo: past.length > 0,
      canRedo: future.length > 0,
      undo,
      redo,
      push,
      saveCheckpoint,
      history: past,
      currentPosition: past.length,
    }),
    [future.length, past, push, redo, saveCheckpoint, undo]
  );

  return <UndoContext.Provider value={value}>{children}</UndoContext.Provider>;
}

export function useUndoRedo(): UndoContextValue {
  const ctx = useContext(UndoContext);
  if (!ctx) throw new Error("useUndoRedo must be used inside UndoProvider");
  return ctx;
}
