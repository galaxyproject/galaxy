/**
 * Collection creation related types and interfaces.
 * Co-located with collection creation logic for better cohesion.
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
 * Collection configuration used by upload orchestration.
 */
export interface UploadCollectionConfig extends CollectionCreationInput {
    /** Whether to hide source datasets after collection creation */
    hideSourceItems: boolean;
    /** Target history ID where the collection will be created */
    historyId: string;
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
