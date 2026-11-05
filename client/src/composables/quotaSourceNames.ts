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

    // The storages load when the store is first used, so only once a name is needed: most pages show none.
    const storeNamesBySource = computed(() => {
        const namesBySource: Record<string, string[]> = {};
        for (const store of useObjectStoreStore().selectableObjectStores ?? []) {
            const source = store.quota.source;
            // A storage with its quota disabled doesn't count toward its source
            if (source && store.quota.enabled && store.name) {
                (namesBySource[source] ??= []).push(store.name);
            }
        }
        return namesBySource;
    });

    function quotaSourceName(sourceLabel: string | null): string {
        if (sourceLabel === null) {
            return localize("Default storage");
        }
        return storeNamesBySource.value[sourceLabel]?.join(" / ") ?? sourceLabel;
    }

    /** Names of the storage sources other than the default one whose quota the user exceeded. */
    const otherSourcesOverQuotaNames = computed(() =>
        quotaUsageStore.otherSourcesOverQuota.map((usage) => quotaSourceName(usage.rawSourceLabel)).join(", "),
    );

    return { quotaSourceName, otherSourcesOverQuotaNames };
}
