import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createGalaxyApi } from './client';

// Create a mock API client for testing
const mockApiClient = {
  GET: vi.fn(),
  POST: vi.fn(),
  PUT: vi.fn(),
  DELETE: vi.fn(),
  PATCH: vi.fn(),
};

// Mock createClient before importing
vi.mock('openapi-fetch', () => {
  return {
    default: vi.fn().mockImplementation(() => mockApiClient)
  };
});

import createClient from 'openapi-fetch';

describe('Galaxy API Client', () => {
  beforeEach(() => {
    // Reset mock function calls before each test
    vi.clearAllMocks();
  });

  it('creates a client with the default base URL', () => {
    // Set up window.location.origin for testing
    const originalLocation = window.location;
    delete (window as any).location;
    window.location = { ...originalLocation, origin: 'https://test-galaxy.org' } as any;

    const api = createGalaxyApi();
    
    expect(createClient).toHaveBeenCalledWith({ baseUrl: 'https://test-galaxy.org' });
    
    // Restore window.location
    window.location = originalLocation;
  });

  it('creates a client with a custom base URL', () => {
    const customUrl = 'https://usegalaxy.org';
    const api = createGalaxyApi(customUrl);
    
    expect(createClient).toHaveBeenCalledWith({ baseUrl: customUrl });
  });

  it('strips trailing slash from base URL', () => {
    const customUrl = 'https://usegalaxy.org/';
    const expectedUrl = 'https://usegalaxy.org';
    const api = createGalaxyApi(customUrl);
    
    expect(createClient).toHaveBeenCalledWith({ baseUrl: expectedUrl });
  });

  it('returns the configured client', () => {
    const api = createGalaxyApi();
    
    // Should have all the HTTP methods
    expect(api).toEqual(mockApiClient);
    expect(api).toHaveProperty('GET');
    expect(api).toHaveProperty('POST');
    expect(api).toHaveProperty('PUT');
    expect(api).toHaveProperty('DELETE');
    expect(api).toHaveProperty('PATCH');
  });
});