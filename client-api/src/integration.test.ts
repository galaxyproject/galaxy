import { describe, it, expect, vi, beforeEach } from 'vitest';
import { type HistorySummary } from './api-types';

// Set up mock responses
const mockHistories: HistorySummary[] = [
  {
    id: '1',
    name: 'Test History 1',
    deleted: false,
    purged: false,
    archived: false,
    tags: [],
    model_class: 'History',
    url: '/api/histories/1',
  },
  {
    id: '2',
    name: 'Test History 2',
    deleted: false,
    purged: false,
    archived: false,
    tags: ['test'],
    model_class: 'History',
    url: '/api/histories/2',
  },
];

// Create a mock API client with typed responses
const mockApiClient = {
  GET: vi.fn().mockImplementation((path, options) => {
    if (path === '/api/histories') {
      return Promise.resolve({
        data: mockHistories,
        error: null,
        response: new Response(),
      });
    }
    if (path === '/api/histories/{history_id}' && 
        options?.params?.path?.history_id === '1') {
      return Promise.resolve({
        data: mockHistories[0],
        error: null,
        response: new Response(),
      });
    }
    return Promise.resolve({
      data: null,
      error: { status: 404, message: 'Not found' },
      response: new Response(),
    });
  }),
  POST: vi.fn(),
  PUT: vi.fn(),
  DELETE: vi.fn(),
  PATCH: vi.fn(),
};

// Setup mocks before importing the modules that use them
vi.mock('openapi-fetch', () => {
  return {
    default: vi.fn().mockImplementation(() => mockApiClient)
  };
});

// Import the modules after setting up mocks
import { createGalaxyApi, GalaxyApi } from './index';

describe('Galaxy API Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('exports the createGalaxyApi function', () => {
    expect(typeof createGalaxyApi).toBe('function');
  });

  it('exports the backward-compatible GalaxyApi function', () => {
    expect(typeof GalaxyApi).toBe('function');
    expect(GalaxyApi()).toEqual(mockApiClient);
  });

  it('retrieves histories with proper typing', async () => {
    const api = createGalaxyApi();
    const { data, error } = await api.GET('/api/histories');
    
    expect(error).toBeNull();
    expect(data).toEqual(mockHistories);
    
    if (data) {
      // This is a type check - if TypeScript can compile this, 
      // it means the types are working correctly
      const firstHistory = data[0];
      expect(firstHistory.id).toBe('1');
      expect(firstHistory.name).toBe('Test History 1');
    }
  });

  it('retrieves a single history by ID', async () => {
    const api = createGalaxyApi();
    const { data, error } = await api.GET('/api/histories/{history_id}', {
      params: {
        path: {
          history_id: '1'
        }
      }
    });
    
    expect(error).toBeNull();
    expect(data).toEqual(mockHistories[0]);
  });

  it('handles errors properly', async () => {
    const api = createGalaxyApi();
    const { data, error } = await api.GET('/api/nonexistent');
    
    expect(data).toBeNull();
    expect(error).toEqual({ status: 404, message: 'Not found' });
  });
});