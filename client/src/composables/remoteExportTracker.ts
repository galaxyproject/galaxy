import { onMounted, type Ref, ref } from "vue";

import { fetchUserExportRecords } from "@/api/exports";
import type { ExportRecord } from "@/components/Common/models/exportRecordModel";

/**
 * Composable to track remote exports (exports to file sources).
 * Fetches export records from the API and provides reactive data.
 */
export function useRemoteExportTracker() {
    const remoteExports: Ref<ExportRecord[]> = ref([]);
    const isLoading = ref(false);
    const error = ref<string | null>(null);

    async function fetchExports(limit = 50, days = 30) {
        isLoading.value = true;
        error.value = null;
        try {
            const records = await fetchUserExportRecords(limit, days);
            remoteExports.value = records;
        } catch (e) {
            error.value = e instanceof Error ? e.message : "Failed to fetch exports";
            console.error("Failed to fetch remote exports:", e);
        } finally {
            isLoading.value = false;
        }
    }

    async function refresh() {
        await fetchExports();
    }

    // Fetch on mount
    onMounted(() => {
        fetchExports();
    });

    return {
        remoteExports,
        isLoading,
        error,
        refresh,
        fetchExports,
    };
}
