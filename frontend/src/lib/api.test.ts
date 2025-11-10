import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Use vi.hoisted() to create mocks that survive hoisting
const { mockGet, mockPost, mockPatch, mockDelete } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
  mockPatch: vi.fn(),
  mockDelete: vi.fn(),
}));

// Mock axios before importing api
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: mockGet,
      post: mockPost,
      patch: mockPatch,
      delete: mockDelete,
    })),
  },
}));

// Import after mocking
import {
  listPersons,
  updatePerson,
  deletePerson,
  listSources,
  uploadFiles,
  exportGedcom,
} from './api';

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('listPersons', () => {
    it('should fetch persons list', async () => {
      const mockPersons = [
        { id: 1, name: 'John Doe', gen: 1 },
        { id: 2, name: 'Jane Doe', gen: 2 },
      ];

      mockGet.mockResolvedValue({ data: mockPersons });

      const result = await listPersons();

      expect(mockGet).toHaveBeenCalledWith('/persons', { params: {} });
      expect(result).toEqual(mockPersons);
    });

    it('should pass query parameters', async () => {
      const mockPersons = [{ id: 1, name: 'John Doe' }];
      mockGet.mockResolvedValue({ data: mockPersons });

      await listPersons({ source_id: 1, gen: 2, q: 'John' });

      expect(mockGet).toHaveBeenCalledWith('/persons', {
        params: { source_id: 1, gen: 2, q: 'John' },
      });
    });
  });

  describe('updatePerson', () => {
    it('should update a person', async () => {
      const mockPerson = { id: 1, name: 'John Smith' };
      const payload = { name: 'John Smith' };

      mockPatch.mockResolvedValue({ data: mockPerson });

      const result = await updatePerson(1, payload);

      expect(mockPatch).toHaveBeenCalledWith('/persons/1', payload);
      expect(result).toEqual(mockPerson);
    });
  });

  describe('deletePerson', () => {
    it('should delete a person', async () => {
      mockDelete.mockResolvedValue({ data: null });

      await deletePerson(1);

      expect(mockDelete).toHaveBeenCalledWith('/persons/1');
    });
  });

  describe('listSources', () => {
    it('should fetch sources list', async () => {
      const mockSources = [
        { id: 1, name: 'chart.pdf', path: '/uploads/chart.pdf' },
        { id: 2, name: 'tree.pdf', path: '/uploads/tree.pdf' },
      ];

      mockGet.mockResolvedValue({ data: mockSources });

      const result = await listSources();

      expect(mockGet).toHaveBeenCalledWith('/files');
      expect(result).toEqual(mockSources);
    });
  });

  describe('uploadFiles', () => {
    it('should upload files', async () => {
      const mockFiles = [new File(['content'], 'test.pdf', { type: 'application/pdf' })];
      const mockResponse = [{ id: 1, name: 'test.pdf' }];

      mockPost.mockResolvedValue({ data: mockResponse });

      const result = await uploadFiles(mockFiles);

      expect(mockPost).toHaveBeenCalledWith(
        '/files/upload',
        expect.any(FormData)
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('exportGedcom', () => {
    it('should export GEDCOM file as blob', async () => {
      const mockBlob = new Blob(['GEDCOM content'], { type: 'application/x-gedcom' });

      mockPost.mockResolvedValue({ data: mockBlob });

      const result = await exportGedcom();

      expect(mockPost).toHaveBeenCalledWith(
        '/export/gedcom',
        undefined,
        { responseType: 'blob' }
      );
      expect(result).toEqual(mockBlob);
    });
  });

  describe('Error Handling', () => {
    it('should throw error when API call fails', async () => {
      const mockError = new Error('Network error');
      mockGet.mockRejectedValue(mockError);

      await expect(listPersons()).rejects.toThrow();
    });

    it('should propagate errors from failed API calls', async () => {
      const mockError = new Error('API Error');
      mockPatch.mockRejectedValue(mockError);

      await expect(updatePerson(999, { name: 'Test' })).rejects.toThrow();
    });
  });
});
