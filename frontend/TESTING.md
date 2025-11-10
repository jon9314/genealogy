# Frontend Testing Guide

## Overview

This genealogy workstation frontend uses **Vitest** + **React Testing Library** for comprehensive test coverage.

**Technology Stack:**
- **Test Runner:** Vitest 1.2+
- **Testing Library:** @testing-library/react 14+
- **DOM Environment:** happy-dom
- **User Interactions:** @testing-library/user-event 14+
- **Assertions:** @testing-library/jest-dom matchers

---

## Quick Start

### Install Dependencies

Dependencies are already configured in `package.json`. If you need to reinstall:

```bash
cd frontend
npm install
```

### Run Tests

```bash
# Watch mode (re-runs on file changes) - DEFAULT
npm test

# Run once and exit
npm run test:run

# Interactive UI mode (best for debugging)
npm run test:ui

# Generate coverage report
npm run test:coverage
```

---

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── PersonForm.tsx
│   │   └── PersonForm.test.tsx       ✅ Component test
│   ├── hooks/
│   │   ├── useUndoRedo.tsx
│   │   └── useUndoRedo.test.tsx      ✅ Hook test
│   ├── lib/
│   │   ├── api.ts
│   │   └── api.test.ts               ✅ Utility test
│   └── test/
│       └── setup.ts                  ⚙️ Global test setup
├── vitest.config.ts                  ⚙️ Vitest configuration
└── TESTING.md                        📖 This file
```

---

## Writing Tests

### 1. Component Tests

**Example: `PersonForm.test.tsx`**

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PersonForm from './PersonForm';

describe('PersonForm', () => {
  it('should render the form with person data', () => {
    const mockPerson = {
      id: 1,
      name: 'John Doe',
      // ... other fields
    };
    const onSubmit = vi.fn();
    const onClose = vi.fn();

    render(<PersonForm person={mockPerson} onSubmit={onSubmit} onClose={onClose} />);

    expect(screen.getByDisplayValue('John Doe')).toBeInTheDocument();
  });

  it('should call onSubmit when form is submitted', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const onClose = vi.fn();

    render(<PersonForm person={mockPerson} onSubmit={onSubmit} onClose={onClose} />);

    const submitButton = screen.getByText(/save/i);
    await user.click(submitButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledOnce();
    });
  });
});
```

**Best Practices:**
- ✅ Use `screen.getByRole()` for accessibility-compliant queries
- ✅ Use `waitFor()` for async assertions
- ✅ Use `userEvent` instead of `fireEvent` for realistic interactions
- ✅ Test user flows, not implementation details
- ✅ Mock props with `vi.fn()` for callbacks

---

### 2. Hook Tests

**Example: `useUndoRedo.test.tsx`**

```typescript
import { renderHook, act, waitFor } from '@testing-library/react';
import { UndoProvider, useUndoRedo } from './useUndoRedo';

const wrapper = ({ children }) => <UndoProvider>{children}</UndoProvider>;

describe('useUndoRedo', () => {
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
    expect(result.current.canUndo).toBe(true);
  });
});
```

**Best Practices:**
- ✅ Wrap hooks that use context with provider
- ✅ Use `act()` for state updates
- ✅ Test state transitions, not internal state
- ✅ Use `waitFor()` for async hook updates

---

### 3. Utility/API Tests

**Example: `api.test.ts`**

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import { listPersons, updatePerson } from './api';

vi.mock('axios');
const mockedAxios = axios as any;

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch persons list', async () => {
    const mockPersons = [{ id: 1, name: 'John Doe' }];
    mockedAxios.get.mockResolvedValue({ data: mockPersons });

    const result = await listPersons();

    expect(mockedAxios.get).toHaveBeenCalledWith('/persons', { params: {} });
    expect(result).toEqual(mockPersons);
  });
});
```

**Best Practices:**
- ✅ Mock external dependencies (`axios`, `fetch`, etc.)
- ✅ Clear mocks in `beforeEach()` for test isolation
- ✅ Test both success and error paths
- ✅ Verify function calls with `.toHaveBeenCalledWith()`

---

## Common Testing Patterns

### Pattern 1: Finding Elements

```typescript
// By role (most accessible)
screen.getByRole('button', { name: /save/i });
screen.getByRole('textbox', { name: /name/i });

// By label text
screen.getByLabelText(/given name/i);

// By display value (for inputs)
screen.getByDisplayValue('John Doe');

// By text content
screen.getByText(/submit/i);

// Query (returns null if not found)
screen.queryByText(/not found/);

// Find (async, waits for element)
await screen.findByText(/loading complete/);
```

### Pattern 2: User Interactions

```typescript
const user = userEvent.setup();

// Click
await user.click(screen.getByRole('button'));

// Type
await user.type(screen.getByRole('textbox'), 'Hello World');

// Clear input
await user.clear(screen.getByRole('textbox'));

// Select option
await user.selectOptions(screen.getByRole('combobox'), 'option1');

// Check checkbox
await user.click(screen.getByRole('checkbox'));
```

### Pattern 3: Async Testing

```typescript
// Wait for element to appear
await waitFor(() => {
  expect(screen.getByText(/success/i)).toBeInTheDocument();
});

// Wait for assertion
await waitFor(() => {
  expect(mockFn).toHaveBeenCalled();
});

// Find element (built-in wait)
const element = await screen.findByText(/loaded/i);
```

### Pattern 4: Mocking Functions

```typescript
// Mock callback
const onSubmit = vi.fn();

// Mock async function
const onSubmit = vi.fn().mockResolvedValue({ id: 1 });

// Mock with implementation
const onSubmit = vi.fn((data) => {
  console.log('Submitted:', data);
  return { success: true };
});

// Verify calls
expect(onSubmit).toHaveBeenCalledOnce();
expect(onSubmit).toHaveBeenCalledWith({ name: 'John' });
expect(onSubmit).toHaveBeenCalledTimes(2);

// Clear mock history
onSubmit.mockClear();
```

---

## Available Matchers

From `@testing-library/jest-dom`:

```typescript
// Presence
expect(element).toBeInTheDocument();
expect(element).toBeVisible();
expect(element).toBeEmptyDOMElement();

// Attributes
expect(element).toHaveAttribute('href', '/about');
expect(element).toHaveClass('active');
expect(input).toHaveValue('John Doe');
expect(input).toBeDisabled();
expect(input).toBeRequired();

// Text content
expect(element).toHaveTextContent('Hello World');
expect(element).toHaveTextContent(/hello/i);

// Form elements
expect(checkbox).toBeChecked();
expect(input).toHaveFocus();
```

---

## Configuration Files

### `vitest.config.ts`

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,                    // Use global test functions
    environment: 'happy-dom',          // Fast DOM simulation
    setupFiles: ['./src/test/setup.ts'], // Global setup
    css: true,                         // Process CSS imports
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
      ],
    },
  },
});
```

### `src/test/setup.ts`

Global test setup:
- Extends Vitest's `expect` with jest-dom matchers
- Cleans up after each test
- Mocks `window.matchMedia`
- Mocks `window.alert` and `window.confirm`

---

## Testing Best Practices

### ✅ DO

1. **Test user behavior, not implementation**
   ```typescript
   // ✅ Good
   await user.click(screen.getByRole('button', { name: /save/i }));
   expect(onSubmit).toHaveBeenCalled();

   // ❌ Bad
   expect(component.state.saving).toBe(true);
   ```

2. **Use accessible queries**
   ```typescript
   // ✅ Good
   screen.getByRole('button', { name: /submit/i });
   screen.getByLabelText(/email/i);

   // ❌ Bad
   screen.getByTestId('submit-btn');
   screen.getByClassName('email-input');
   ```

3. **Test error states**
   ```typescript
   it('should show error when API call fails', async () => {
     mockApi.get.mockRejectedValue(new Error('Network error'));

     render(<MyComponent />);

     await waitFor(() => {
       expect(screen.getByText(/error/i)).toBeInTheDocument();
     });
   });
   ```

4. **Clean up resources**
   ```typescript
   afterEach(() => {
     vi.clearAllMocks();
     cleanup();  // Automatically called by setup.ts
   });
   ```

### ❌ DON'T

1. **Don't test implementation details**
   - Avoid testing internal state
   - Avoid testing private functions
   - Avoid testing CSS classes directly

2. **Don't use brittle selectors**
   - Avoid `getByTestId` (use semantic queries)
   - Avoid `.querySelector()` (use Testing Library queries)

3. **Don't forget to await async operations**
   ```typescript
   // ❌ Bad
   user.click(button);
   expect(onSubmit).toHaveBeenCalled();

   // ✅ Good
   await user.click(button);
   await waitFor(() => {
     expect(onSubmit).toHaveBeenCalled();
   });
   ```

---

## Debugging Tests

### 1. Print DOM

```typescript
import { screen } from '@testing-library/react';

// Print entire document
screen.debug();

// Print specific element
screen.debug(screen.getByRole('button'));
```

### 2. Use UI Mode

```bash
npm run test:ui
```

Opens interactive browser interface with:
- Test results
- Source code
- Console output
- DOM snapshots

### 3. VSCode Integration

Install extension: **Vitest** by Vitest Team

Features:
- Run tests from editor
- See test results inline
- Debug tests with breakpoints

---

## Coverage Reports

Generate coverage:

```bash
npm run test:coverage
```

View report:

```bash
open coverage/index.html
```

**Coverage Goals:**
- **Statements:** 80%+
- **Branches:** 75%+
- **Functions:** 80%+
- **Lines:** 80%+

---

## Example Test Files

### ✅ Already Created

1. **`useUndoRedo.test.tsx`** - Hook testing example
   - Tests undo/redo functionality
   - Tests async operations
   - Tests edge cases

2. **`PersonForm.test.tsx`** - Component testing example
   - Tests form rendering
   - Tests user interactions
   - Tests form submission

3. **`api.test.ts`** - Utility testing example
   - Tests API calls
   - Tests error handling
   - Tests mocking

### 📝 To Be Created

Recommended tests for critical components:

1. **`Table.test.tsx`** - Data grid functionality
2. **`GraphView.test.tsx`** - Family tree visualization
3. **`Review.test.tsx`** - Duplicate resolution
4. **`Search.test.tsx`** - Global search and filters
5. **`UndoHistoryViewer.test.tsx`** - History modal

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Frontend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: cd frontend && npm ci

      - name: Run tests
        run: cd frontend && npm run test:run

      - name: Generate coverage
        run: cd frontend && npm run test:coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./frontend/coverage/coverage-final.json
```

---

## Troubleshooting

### Issue: "Cannot find module '@testing-library/react'"

**Solution:**
```bash
cd frontend
npm install
```

### Issue: "window.matchMedia is not a function"

**Solution:** Already fixed in `src/test/setup.ts`. If issue persists, check setup file is loaded.

### Issue: "Element not found" but it's visible in debug output

**Solution:** Element may not be in document yet. Use `await screen.findBy...()` or `waitFor()`.

### Issue: Tests pass locally but fail in CI

**Solution:**
- Ensure `npm ci` is used (not `npm install`)
- Check Node version matches local
- Add `--no-cache` flag to test command

---

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [Testing Library Queries](https://testing-library.com/docs/queries/about)
- [jest-dom Matchers](https://github.com/testing-library/jest-dom)
- [Common Testing Mistakes](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

---

## Next Steps

1. **Run existing tests:**
   ```bash
   cd frontend
   npm test
   ```

2. **Create tests for your components:**
   - Copy examples from `PersonForm.test.tsx`
   - Follow patterns in this guide
   - Aim for 80%+ coverage

3. **Add tests to your workflow:**
   - Run tests before committing
   - Add pre-commit hook (optional)
   - Set up CI/CD pipeline

---

## Summary

✅ **Test infrastructure is ready!**
✅ **Example tests created for:** Hooks, Components, API Utils
✅ **Run `npm test` to start testing**

For questions or issues, refer to the resources above or check the example test files.
