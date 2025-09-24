import { createContext, ReactNode, useCallback, useContext, useMemo, useState } from "react";

type UndoAction = {
  label: string;
  redo: () => Promise<void> | void;
  undo: () => Promise<void> | void;
};

type UndoContextValue = {
  canUndo: boolean;
  canRedo: boolean;
  undo: () => Promise<void>;
  redo: () => Promise<void>;
  push: (action: UndoAction, immediate?: boolean) => Promise<void>;
  history: UndoAction[];
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

  const value = useMemo<UndoContextValue>(
    () => ({
      canUndo: past.length > 0,
      canRedo: future.length > 0,
      undo,
      redo,
      push,
      history: past,
    }),
    [future.length, past, push, redo, undo]
  );

  return <UndoContext.Provider value={value}>{children}</UndoContext.Provider>;
}

export function useUndoRedo(): UndoContextValue {
  const ctx = useContext(UndoContext);
  if (!ctx) throw new Error("useUndoRedo must be used inside UndoProvider");
  return ctx;
}
