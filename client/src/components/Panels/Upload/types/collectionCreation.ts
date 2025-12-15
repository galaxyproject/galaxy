/**
 * Collection creation related types and interfaces
 */

/**
 * Supported collection types in Galaxy
 */
export type SupportedCollectionType = "list" | "list:paired";

/**
 * Collection creation input from UI components
 */
export interface CollectionCreationInput {
    /** Name of the collection to create */
    name: string;
    /** Type of collection: 'list' or 'list:paired' */
    type: SupportedCollectionType;
}

/**
 * Validation state for a collection configuration
 */
export interface CollectionValidationState {
    /** Whether the collection configuration is valid */
    isValid: boolean;
    /** Whether collection creation is active */
    isActive: boolean;
    /** Validation error message if invalid */
    message: string;
}

/**
 * Complete state of collection creation including configuration and validation
 */
export interface CollectionCreationState {
    /** The collection configuration if valid and active, otherwise null */
    config: CollectionCreationInput | null;
    /** Validation state including active status and validity */
    validation: CollectionValidationState;
}

/**
 * Type options for collection creation
 */
export interface CollectionTypeOption {
    value: SupportedCollectionType;
    text: string;
}
