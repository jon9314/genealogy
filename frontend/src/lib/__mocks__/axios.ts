import { vi } from 'vitest';

export const mockClient = {
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
};

export default {
  create: vi.fn(() => mockClient),
  ...mockClient,
};
