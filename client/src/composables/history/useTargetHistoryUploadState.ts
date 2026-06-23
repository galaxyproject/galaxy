import { computed, type ComputedRef } from "vue";

import type { AnyHistory } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";
import {
    getHistoryUploadBlockReason,
    getHistoryUploadWarningMessage,
    type HistoryUploadBlockReason,
} from "@/utils/historyUpload";

interface TargetHistoryUploadState {
    targetHistory: ComputedRef<AnyHistory | null>;
    uploadBlockReason: ComputedRef<HistoryUploadBlockReason | null>;
    warningMessage: ComputedRef<string>;
}

export function useTargetHistoryUploadState(
    targetHistoryId: ComputedRef<string | null | undefined>,
): TargetHistoryUploadState {
    const historyStore = useHistoryStore();

    const targetHistory = computed(() => {
        const historyId = targetHistoryId.value;
        return historyId ? historyStore.getHistoryById(historyId, false) : null;
    });

    const uploadBlockReason = computed(() => getHistoryUploadBlockReason(targetHistory.value));
    const warningMessage = computed(() => getHistoryUploadWarningMessage(uploadBlockReason.value));

    return {
        targetHistory,
        uploadBlockReason,
        warningMessage,
    };
}
