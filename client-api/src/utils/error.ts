/**
 * Simple error handling utilities for Galaxy Client API
 */

/**
 * Convert various error formats to a readable string message
 */
export function errorMessageAsString(error: any): string {
  if (typeof error === 'string') {
    return error;
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  if (error && typeof error === 'object') {
    // Handle API response errors
    if (error.status && error.error) {
      return `API Error (${error.status}): ${error.error}`;
    }
    
    // Handle response objects with error message
    if (error.message) {
      return error.message;
    }
    
    // Try to stringify the error object
    try {
      return JSON.stringify(error);
    } catch (e) {
      // Fall back to object inspection
      return String(error);
    }
  }
  
  return 'Unknown error';
}