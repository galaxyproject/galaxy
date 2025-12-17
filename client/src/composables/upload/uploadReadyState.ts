import { computed, type ComputedRef, type Ref } from "vue";

import type { CollectionCreationState } from "@/components/Panels/Upload/types/collectionCreation";

/**
 * Composable for determining if upload items are ready to be uploaded.
 * Consolidates validation logic across multiple upload methods.
 *
 * @example
 * ```typescript
 * const hasItems = computed(() => items.value.length > 0);
 * const hasInvalidItems = computed(() => items.value.some(item => !isValid(item)));
 *
 * const { isReadyToUpload } = useUploadReadyState(
 *   hasItems,
 *   collectionState,
 *   hasInvalidItems
 * );
 *
 * // Use in template or watch
 * watch(isReadyToUpload, (ready) => emit("ready", ready));
 * ```
 *
 * @param hasItems - Computed/ref indicating if any items exist
 * @param collectionState - Reactive reference to collection creation state
 * @param additionalValidation - Optional computed/ref for method-specific validation (e.g., URL validation)
 * @returns Object with isReadyToUpload computed property
 */
export function useUploadReadyState(
    hasItems: ComputedRef<boolean> | Ref<boolean>,
    collectionState: Ref<CollectionCreationState>,
    additionalValidation?: ComputedRef<boolean> | Ref<boolean>,
) {
    /**
     * Computed property that determines if upload can proceed.
     * Checks:
     * 1. Items exist
     * 2. Additional validation passes (if provided)
     * 3. Collection validation passes (if collection creation is active)
     */
    const isReadyToUpload = computed(() => {
        // Must have items to upload
        if (!hasItems.value) {
            return false;
        }

        // Check additional validation if provided
        if (additionalValidation !== undefined && !additionalValidation.value) {
            return false;
        }

        // If collection creation is active, it must be valid
        if (collectionState.value.validation.isActive && !collectionState.value.validation.isValid) {
            return false;
        }

        return true;
    });

    return {
        isReadyToUpload,
    };
}
