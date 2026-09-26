import { onMounted, ref } from "vue";

import { GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

/**
 * One-shot loader for the AI history-summary endpoint. Fetches on mount;
 * exposes loading / error / summary refs for the view.
 */
export function useHistoryGraphSummary(historyId: string) {
    const loading = ref(false);
    const error = ref<string | null>(null);
    const summary = ref<string | null>(null);

    async function load() {
        loading.value = true;
        error.value = null;
        try {
            const {
                data,
                error: apiError,
                response,
            } = await GalaxyApi().POST("/api/ai/agents/history-summary", {
                body: { history_id: historyId },
            });
            if (!response.ok) {
                error.value = errorMessageAsString(apiError, `Request failed with status ${response.status}.`);
                return;
            }
            summary.value = data?.content ?? "";
        } catch (e) {
            error.value = errorMessageAsString(e, "Failed to generate summary.");
        } finally {
            loading.value = false;
        }
    }

    onMounted(load);

    return { loading, error, summary };
}
