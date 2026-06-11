import { storeToRefs } from "pinia";
import { computed, type ComputedRef, type Ref, ref, watch } from "vue";

import type { UserConcreteObjectStoreModel } from "@/api";
import { useObjectStoreStore } from "@/stores/objectStoreStore";
import { useUserStore } from "@/stores/userStore";

interface TargetObjectStoreSelectionState {
    targetObjectStoreId: Ref<string | null>;
    shouldShowObjectStoreSelector: ComputedRef<boolean>;
    objectStoreUploadBlockReason: ComputedRef<string | null>;
    objectStoreDisabledReason: ComputedRef<string | null>;
    handleObjectStoreSelected: (store: UserConcreteObjectStoreModel | null) => void;
}

export function useTargetObjectStoreSelectionState(
    targetHistoryId: Ref<string>,
    advancedMode: ComputedRef<boolean>,
): TargetObjectStoreSelectionState {
    const objectStoreStore = useObjectStoreStore();
    const { selectableObjectStores } = storeToRefs(objectStoreStore);
    const userStore = useUserStore();

    const targetObjectStoreId = ref<string | null>(null);
    const userManuallySelectedStore = ref(false);

    const shouldShowObjectStoreSelector = computed(() => {
        return advancedMode.value && (selectableObjectStores.value?.length ?? 0) > 1;
    });

    const objectStoreDisabledReason = computed(() => {
        if (userStore.isAnonymous) {
            return "Please log in or register to select a storage location.";
        }
        return null;
    });

    const objectStoreUploadBlockReason = computed(() => {
        if (!targetObjectStoreId.value || !selectableObjectStores.value) {
            return null;
        }

        return selectableObjectStores.value.some((store) => store.object_store_id === targetObjectStoreId.value)
            ? null
            : "Selected storage location is no longer available.";
    });

    watch(
        [targetHistoryId, selectableObjectStores],
        ([newHistoryId]) => {
            if (!newHistoryId || userManuallySelectedStore.value) {
                return;
            }

            // Keep null to represent "Use history preference" until the user picks a concrete store.
            targetObjectStoreId.value = null;
        },
        { immediate: true },
    );

    function handleObjectStoreSelected(store: UserConcreteObjectStoreModel | null) {
        userManuallySelectedStore.value = true;
        targetObjectStoreId.value = store?.object_store_id ?? null;
    }

    return {
        targetObjectStoreId,
        shouldShowObjectStoreSelector,
        objectStoreUploadBlockReason,
        objectStoreDisabledReason,
        handleObjectStoreSelected,
    };
}
