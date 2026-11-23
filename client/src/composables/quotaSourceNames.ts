import { computed } from "vue";

import { useObjectStoreStore } from "@/stores/objectStoreStore";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";
import localize from "@/utils/localization";

/**
 * Names quota sources after the storages that use them, as a quota source only has a label.
 * Several storages can share a source; a source without a known storage keeps its label.
 */
export function useQuotaSourceNames() {
    const quotaUsageStore = useQuotaUsageStore();

    function quotaSourceName(sourceLabel: string | null): string {
        if (sourceLabel === null) {
            return localize("Default storage");
        }
        // The storages load when the store is first used, so only once a name is needed: most pages show none.
        return useObjectStoreStore().storeNamesByQuotaSource[sourceLabel]?.join(" / ") ?? sourceLabel;
    }

    /** Names of the storage sources other than the default one whose quota the user exceeded. */
    const otherSourcesOverQuotaNames = computed(() =>
        quotaUsageStore.otherSourcesOverQuota.map((usage) => quotaSourceName(usage.rawSourceLabel)).join(", "),
    );

    return { quotaSourceName, otherSourcesOverQuotaNames };
}
