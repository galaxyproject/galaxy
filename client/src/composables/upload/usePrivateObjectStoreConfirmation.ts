import { type Ref, ref } from "vue";

import type { UserConcreteObjectStoreModel } from "@/api";
import { getPermissions, isHistoryPrivate, makePrivate, type PermissionsResponse } from "@/components/History/services";
import { useConfirmDialog } from "@/composables/confirmDialog";

interface PrivateObjectStoreConfirmationState {
    warningMessage: Ref<string>;
    handlePrivateStoreSelection: (store: UserConcreteObjectStoreModel | null, historyId: string) => Promise<void>;
}

export function usePrivateObjectStoreConfirmation(): PrivateObjectStoreConfirmationState {
    const { confirm } = useConfirmDialog();
    const warningMessage = ref("");

    async function handlePrivateStoreSelection(
        store: UserConcreteObjectStoreModel | null,
        historyId: string,
    ): Promise<void> {
        warningMessage.value = "";

        if (!store?.private || !historyId) {
            return;
        }

        try {
            const { data } = await getPermissions(historyId);
            const permissionResponse = data as PermissionsResponse;
            const historyPrivate = await isHistoryPrivate(permissionResponse);

            if (historyPrivate) {
                return;
            }

            const confirmed = await confirm(
                "Your history currently creates sharable datasets, but the selected storage location is private. Make new datasets private in this history by default?",
                {
                    okText: "Private new datasets",
                    cancelText: "Keep datasets public",
                },
            );

            if (confirmed) {
                await makePrivate(historyId, permissionResponse);
            }
        } catch {
            warningMessage.value =
                "Could not verify history privacy settings for the selected private storage location.";
        }
    }

    return {
        warningMessage,
        handlePrivateStoreSelection,
    };
}
