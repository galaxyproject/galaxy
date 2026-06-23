import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { fetchCurrentUserQuotaSourceUsage, fetchCurrentUserQuotaUsages, type QuotaUsage } from "@/api/users";
import { errorMessageAsString } from "@/utils/simple-error";

const DEFAULT_SOURCE_KEY = "__null__";
const REFRESH_DEBOUNCE_MS = 5000;

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
    const inFlightBySourcePromise = new Map<string, Promise<QuotaUsage | null>>();

    let refreshTimer: ReturnType<typeof setTimeout> | null = null;

    const isLoaded = computed(() => quotaUsages.value !== undefined);

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
    }

    async function refreshNow() {
        if (refreshTimer) {
            clearTimeout(refreshTimer);
            refreshTimer = null;
        }

        await loadQuotaUsages(true);
    }

    function requestRefreshDebounced(delayMs = REFRESH_DEBOUNCE_MS) {
        if (refreshTimer) {
            clearTimeout(refreshTimer);
        }

        refreshTimer = setTimeout(() => {
            refreshTimer = null;
            void loadQuotaUsages(true);
        }, delayMs);
    }

    async function applyRecalculationCompletedRefresh() {
        await refreshNow();
    }

    return {
        quotaUsages,
        sourceUsageByKey,
        loadingAll,
        loadingBySource,
        errorMessage,
        sourceErrorByKey,
        isLoaded,
        getQuotaUsageBySourceLabel,
        loadQuotaUsages,
        loadQuotaUsageForSource,
        requestRefreshDebounced,
        refreshNow,
        applyRecalculationCompletedRefresh,
        invalidate,
    };
});
