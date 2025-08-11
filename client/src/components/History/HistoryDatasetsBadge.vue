<script setup lang="ts">
import { faDatabase, faSave, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { onMounted, ref } from "vue";

import { getHistoryCounts, type HistoryCounts } from "@/api/histories";
import { Toast } from "@/composables/toast";
import { errorMessageAsString } from "@/utils/simple-error";

interface Props {
    historyId: string;
    count?: number;
}

const props = defineProps<Props>();

const loading = ref(true);

const niceSize = ref<HistoryCounts["nice_size"]>();
const contentsActive = ref<HistoryCounts["contents_active"]>();
const contentsStates = ref<HistoryCounts["contents_states"]>();

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
