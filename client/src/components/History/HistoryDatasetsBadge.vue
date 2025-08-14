<script setup lang="ts">
/**
 * HistoryDatasetsBadge Component
 *
 * A specialized badge component that displays dataset information for a history
 * including item count, storage size, and dataset states.
 * The badge is clickable and navigates to the history's storage overview page.
 *
 * Features:
 * - Shows dataset count and storage size
 * - Displays dataset states (running, queued, error, etc.)
 * - Shows counts for deleted and hidden datasets
 * - Responsive design that hides text labels on small screens
 * - Loading state with spinner
 * - Error handling for API failures
 * - Clickable navigation to storage overview
 *
 * @component HistoryDatasetsBadge
 * @example
 * <HistoryDatasetsBadge
 *   :history-id="'abc123'"
 *   :count="42" />
 */

import { faDatabase, faSave, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { onMounted, ref } from "vue";

import { getHistoryCounts, type HistoryCounts } from "@/api/histories";
import { Toast } from "@/composables/toast";
import { errorMessageAsString } from "@/utils/simple-error";

interface Props {
    /**
     * The unique identifier of the history to display dataset information for
     * @type {string}
     */
    historyId: string;

    /**
     * Count of datasets in the history
     * @type {number}
     * @optional
     */
    count?: number;
}

const props = defineProps<Props>();

/** Loading state indicator */
const loading = ref(true);

/** Human-readable storage size (e.g., "1.2 GB") */
const niceSize = ref<HistoryCounts["nice_size"]>();
/** Counts of active datasets by state */
const contentsActive = ref<HistoryCounts["contents_active"]>();
/** Counts of datasets by processing state (running, queued, etc.) */
const contentsStates = ref<HistoryCounts["contents_states"]>();

/**
 * Fetches and sets the history counts data from the API
 * Handles loading state and error reporting
 */
async function getCounts() {
    try {
        const counts = await getHistoryCounts(props.historyId);

        niceSize.value = counts.nice_size;
        contentsActive.value = counts.contents_active;
        contentsStates.value = counts.contents_states;
    } catch (e) {
        Toast.error(`Failed to load history counts: ${errorMessageAsString(e)}`);
    } finally {
        loading.value = false;
    }
}

onMounted(async () => {
    await getCounts();
});
</script>

<template>
    <BBadge
        v-b-tooltip.hover.top.noninteractive
        class="history-datasets d-flex flex-gapx-1 flex-gapy-1 align-items-center outline-badge cursor-pointer font-size-small"
        pill
        :title="`View history storage overview`"
        variant="light"
        :to="`/storage/history/${historyId}`">
        <FontAwesomeIcon v-if="loading" :icon="faSpinner" fixed-width spin />
        <template v-else>
            <small v-if="props.count">
                <FontAwesomeIcon :icon="faDatabase" fixed-width />
                <template v-if="props.count"> {{ props.count }} <span class="items">items</span> </template>
            </small>

            <template v-if="props.count && niceSize"> | </template>

            <small v-if="niceSize">
                <FontAwesomeIcon :icon="faSave" fixed-width />
                {{ niceSize }}
            </small>

            <template
                v-if="
                    (contentsStates && Object.values(contentsStates).some((cs) => cs)) ||
                    (contentsActive && Object.values(contentsActive).some((ca) => ca))
                ">
                |
            </template>

            <span
                v-for="(stateCount, state) of contentsStates"
                :key="state"
                class="stats px-1 rounded"
                :class="`state-color-${state}`">
                {{ stateCount }}
            </span>

            <span v-if="contentsActive?.deleted" class="stats px-1 rounded state-color-deleted">
                {{ contentsActive.deleted }}
            </span>

            <span v-if="contentsActive?.hidden" class="stats px-1 rounded state-color-hidden">
                {{ contentsActive.hidden }}
            </span>
        </template>
    </BBadge>
</template>

<style lang="scss" scoped>
@import "_breakpoints.scss";

.history-datasets {
    font-size: smaller;

    .items {
        @container g-card (max-width: #{$breakpoint-sm}) {
            display: none;
        }
    }

    .stats {
        border-width: 1px;
        border-style: solid;
    }
}
</style>
