import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { fetchCurrentUserQuotaSourceUsage, fetchCurrentUserQuotaUsages, type QuotaUsage } from "@/api/users";
import { errorMessageAsString } from "@/utils/simple-error";

const DEFAULT_SOURCE_KEY = "__null__";

function sourceLabelToKey(sourceLabel?: string | null): string {
    return sourceLabel ?? DEFAULT_SOURCE_KEY;
}

export const useQuotaUsageStore = defineStore("quotaUsageStore", () => {
    const quotaUsages = ref<QuotaUsage[]>();
    const sourceUsageByKey = ref<Record<string, QuotaUsage | null>>({});

    const loadingAll = ref(false);
    const loadingBySource = ref<Record<string, boolean>>({});

    const errorMessage = ref<string>();
    const sourceErrorByKey = ref<Record<string, string | undefined>>({});

    let inFlightAllPromise: Promise<QuotaUsage[] | undefined> | null = null;
    let queuedReloadPromise: Promise<QuotaUsage[] | undefined> | null = null;
    const inFlightBySourcePromise = new Map<string, Promise<QuotaUsage | null>>();

    const isLoaded = computed(() => quotaUsages.value !== undefined);
    /** Whether anything asked for the usage, whether or not it loaded: it then needs reloading after changes. */
    const wasRequested = ref(false);

    /** Storage sources other than the default one whose quota the user exceeded. */
    const otherSourcesOverQuota = computed(
        () => quotaUsages.value?.filter((usage) => usage.rawSourceLabel !== null && usage.isOverQuota) ?? [],
    );

    const getQuotaUsageBySourceLabel = computed(() => {
        return (sourceLabel?: string | null): QuotaUsage | null | undefined => {
            const key = sourceLabelToKey(sourceLabel);
            return sourceUsageByKey.value[key];
        };
    });

    function setSourceUsage(sourceLabel: string | null | undefined, usage: QuotaUsage | null) {
        const key = sourceLabelToKey(sourceLabel);
        sourceUsageByKey.value = {
            ...sourceUsageByKey.value,
            [key]: usage,
        };
    }

    function setSourceLoading(sourceLabel: string | null | undefined, loading: boolean) {
        const key = sourceLabelToKey(sourceLabel);
        loadingBySource.value = {
            ...loadingBySource.value,
            [key]: loading,
        };
    }

    function setSourceError(sourceLabel: string | null | undefined, message?: string) {
        const key = sourceLabelToKey(sourceLabel);
        sourceErrorByKey.value = {
            ...sourceErrorByKey.value,
            [key]: message,
        };
    }

    function hydrateSourceUsageFromAll(usages: QuotaUsage[]) {
        const next = { ...sourceUsageByKey.value };
        for (const usage of usages) {
            next[sourceLabelToKey(usage.rawSourceLabel)] = usage;
        }
        sourceUsageByKey.value = next;
    }

    async function loadQuotaUsages(reload = false): Promise<QuotaUsage[] | undefined> {
        wasRequested.value = true;
        if (inFlightAllPromise && reload) {
            // The request in flight may predate the change that asks for a reload: reload once it's done
            queuedReloadPromise ??= inFlightAllPromise.then(() => {
                queuedReloadPromise = null;
                return loadQuotaUsages(true);
            });
            return queuedReloadPromise;
        }
        if (inFlightAllPromise) {
            return inFlightAllPromise;
        }

        if (!reload && quotaUsages.value !== undefined) {
            return quotaUsages.value;
        }

        inFlightAllPromise = (async () => {
            loadingAll.value = true;
            errorMessage.value = undefined;

            try {
                const usages = await fetchCurrentUserQuotaUsages();
                quotaUsages.value = usages;
                hydrateSourceUsageFromAll(usages);
                return usages;
            } catch (e) {
                errorMessage.value = errorMessageAsString(e);
                return quotaUsages.value;
            } finally {
                loadingAll.value = false;
                inFlightAllPromise = null;
            }
        })();

        return inFlightAllPromise;
    }

    async function loadQuotaUsageForSource(sourceLabel?: string | null, reload = false): Promise<QuotaUsage | null> {
        wasRequested.value = true;
        const key = sourceLabelToKey(sourceLabel);

        if (!reload && sourceUsageByKey.value[key] !== undefined) {
            return sourceUsageByKey.value[key] ?? null;
        }

        if (!reload && quotaUsages.value !== undefined) {
            const usageFromAll =
                quotaUsages.value.find((usage) => usage.rawSourceLabel === (sourceLabel ?? null)) ?? null;
            setSourceUsage(sourceLabel, usageFromAll);
            return usageFromAll;
        }

        const inFlight = inFlightBySourcePromise.get(key);
        if (inFlight) {
            return inFlight;
        }

        const queryPromise = (async () => {
            setSourceLoading(sourceLabel, true);
            setSourceError(sourceLabel, undefined);

            try {
                const usage = await fetchCurrentUserQuotaSourceUsage(sourceLabel);
                setSourceUsage(sourceLabel, usage);
                // Keep the list of all sources, which the over-quota warnings use, as current as this one
                if (usage && quotaUsages.value) {
                    quotaUsages.value = quotaUsages.value.map((existing) =>
                        existing.rawSourceLabel === usage.rawSourceLabel ? usage : existing,
                    );
                }
                return usage;
            } catch (e) {
                setSourceError(sourceLabel, errorMessageAsString(e));
                return sourceUsageByKey.value[key] ?? null;
            } finally {
                setSourceLoading(sourceLabel, false);
                inFlightBySourcePromise.delete(key);
            }
        })();

        inFlightBySourcePromise.set(key, queryPromise);
        return queryPromise;
    }

    function invalidate() {
        quotaUsages.value = undefined;
        sourceUsageByKey.value = {};
        errorMessage.value = undefined;
        sourceErrorByKey.value = {};
        wasRequested.value = false;
    }

    return {
        quotaUsages,
        sourceUsageByKey,
        loadingAll,
        loadingBySource,
        errorMessage,
        sourceErrorByKey,
        isLoaded,
        wasRequested,
        otherSourcesOverQuota,
        getQuotaUsageBySourceLabel,
        loadQuotaUsages,
        loadQuotaUsageForSource,
        invalidate,
    };
});
