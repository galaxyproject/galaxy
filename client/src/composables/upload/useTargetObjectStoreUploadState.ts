import { storeToRefs } from "pinia";
import { computed, type ComputedRef, ref, watch } from "vue";

import type { UserConcreteObjectStoreModel } from "@/api";
import { getPermissions, isHistoryPrivate, type PermissionsResponse } from "@/components/History/services";
import { useObjectStoreStore } from "@/stores/objectStoreStore";

interface TargetObjectStoreUploadState {
    selectedStore: ComputedRef<UserConcreteObjectStoreModel | null>;
    storeName: ComputedRef<string>;
    storeDescription: ComputedRef<string>;
    uploadBlockReason: ComputedRef<string | null>;
    warningMessage: ComputedRef<string>;
}

export function useTargetObjectStoreUploadState(
    targetObjectStoreId: ComputedRef<string | null | undefined>,
    targetHistoryId?: ComputedRef<string | null | undefined>,
): TargetObjectStoreUploadState {
    const objectStoreStore = useObjectStoreStore();
    const { selectableObjectStores } = storeToRefs(objectStoreStore);
    const historyIsPrivate = ref<boolean | null>(null);
    const historyPrivacyError = ref(false);

    watch(
        targetHistoryId ?? computed(() => null),
        async (historyId, _previousHistoryId, onCleanup) => {
            historyIsPrivate.value = null;
            historyPrivacyError.value = false;

            if (!historyId) {
                return;
            }

            let isActive = true;
            onCleanup(() => {
                isActive = false;
            });

            try {
                const { data } = await getPermissions(historyId);
                if (!isActive) {
                    return;
                }
                historyIsPrivate.value = await isHistoryPrivate(data as PermissionsResponse);
            } catch {
                if (!isActive) {
                    return;
                }
                historyPrivacyError.value = true;
            }
        },
        { immediate: true },
    );

    const selectedStore = computed(() => {
        const objectStoreId = targetObjectStoreId.value;
        if (!objectStoreId) {
            return null;
        }

        const stores = selectableObjectStores.value;
        if (!stores) {
            return null;
        }

        return stores.find((store) => store.object_store_id === objectStoreId) ?? null;
    });

    const uploadBlockReason = computed(() => {
        const objectStoreId = targetObjectStoreId.value;
        const stores = selectableObjectStores.value;

        if (!objectStoreId || !stores) {
            return null;
        }

        return selectedStore.value ? null : "Selected storage location is no longer available.";
    });

    const warningMessage = computed(() => uploadBlockReason.value ?? "");

    const privacyWarningMessage = computed(() => {
        if (!selectedStore.value?.private) {
            return "";
        }
        if (historyPrivacyError.value) {
            return "Could not verify history privacy settings for the selected private storage location.";
        }
        if (historyIsPrivate.value === false) {
            return "Selected storage location is private while this history still allows sharable datasets.";
        }
        return "";
    });

    const storeName = computed(() => {
        if (selectedStore.value?.name) {
            return selectedStore.value.name;
        }
        return "History preference";
    });

    const storeDescription = computed(() => {
        if (selectedStore.value?.description) {
            return selectedStore.value.description;
        }
        return "Uploads will use the target history storage preference.";
    });

    return {
        selectedStore,
        storeName,
        storeDescription,
        uploadBlockReason,
        warningMessage: computed(() => warningMessage.value || privacyWarningMessage.value),
    };
}
