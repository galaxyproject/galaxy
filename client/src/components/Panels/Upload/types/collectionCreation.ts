/**
 * Collection creation related types and interfaces
 */

import type { SupportedCollectionType } from "@/components/Panels/Upload/uploadState";
import type { CollectionCreationInput } from "@/composables/uploadQueue";

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
