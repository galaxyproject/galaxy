import { watchImmediate } from "@vueuse/core";
import { storeToRefs } from "pinia";

import { isRegisteredUser } from "@/api";
import { useConfigStore } from "@/stores/configurationStore";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";
import { useUserStore } from "@/stores/userStore";

/** Whether the server has quotas on storage sources other than the default one. */
export function hasOtherQuotaSources(config?: { enable_quotas?: boolean; quota_source_labels?: string[] } | null) {
    return Boolean(config?.enable_quotas && config?.quota_source_labels?.length);
}

/** Loads the usage of every storage source for registered users; once loaded, storage refreshes keep it current. */
export function useOtherQuotaSourcesUsage() {
    const configStore = useConfigStore();
    const { currentUser } = storeToRefs(useUserStore());
    const quotaUsageStore = useQuotaUsageStore();

    watchImmediate(
        () => hasOtherQuotaSources(configStore.config) && isRegisteredUser(currentUser.value),
        (shouldLoad) => {
            if (shouldLoad) {
                void quotaUsageStore.loadQuotaUsages();
            }
        },
    );
}
