import { type CleanupOperation } from ".";

/**
 * Defines a new category to display in the Storage Management Dashboard to
 * to provide a set of cleanup operations to free-up some storage space.
 */
export interface CleanupCategory {
    /**
     * The ID of this category.
     */
    id: string;

    /**
     * The name of this category.
     */
    name: string;

    /**
     * The list of available cleanup operations associated with this category.
     */
    operations: CleanupOperation[];
}
