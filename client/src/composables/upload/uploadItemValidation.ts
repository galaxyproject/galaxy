/**
 * Composable for validating upload item properties.
 * Provides validation functions for item names and name restoration logic.
 *
 * @example
 * ```typescript
 * const { isNameValid, restoreOriginalName } = useUploadItemValidation();
 *
 * // In template
 * <BFormInput :state="isNameValid(item.name)" @blur="restoreOriginalName(item, 'default.txt')" />
 * ```
 */
export function useUploadItemValidation() {
    /**
     * Validates that a name is non-empty after trimming whitespace.
     * Returns null for valid names (Bootstrap-Vue convention for valid state).
     *
     * @param name - The name to validate
     * @returns null if valid (non-empty), false if invalid (empty)
     */
    function isNameValid(name: string): boolean | null {
        return name.trim().length > 0 ? null : false;
    }

    /**
     * Restores an item's name to a default value if it's empty.
     * Useful for blur handlers to ensure items always have valid names.
     *
     * @param item - The item with a name property to restore
     * @param defaultName - The default name to use if current name is empty
     */
    function restoreOriginalName<T extends { name: string }>(item: T, defaultName: string): void {
        if (!item.name.trim()) {
            item.name = defaultName;
        }
    }

    return {
        isNameValid,
        restoreOriginalName,
    };
}
