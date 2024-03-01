<script setup lang="ts">
import axios from "axios";
import { onMounted, type Ref, ref, watch } from "vue";

import { withPrefix } from "@/utils/redirect";
import { rethrowSimple } from "@/utils/simple-error";

interface Props {
    historyId?: string;
}
const props = defineProps<Props>();

interface HistoryStats {
    nice_size: string;
    contents_active: {
        deleted?: number;
        hidden?: number;
        active?: number;
    };
    contents_states: {
        error?: number;
        ok?: number;
        new?: number;
        running?: number;
        queued?: number;
    };
}
const historyStats: Ref<HistoryStats | null> = ref(null);

async function getCounts() {
    historyStats.value = null;
    if (props.historyId) {
        try {
            const { data } = await axios.get(
                withPrefix(`/api/histories/${props.historyId}?keys=nice_size,contents_active,contents_states`)
            );
            historyStats.value = data;
        } catch (e) {
            rethrowSimple(e);
        }
    }
}

onMounted(() => {
    getCounts();
});

watch(
    () => props.historyId,
    () => getCounts()
);
</script>

<template>
    <span v-if="historyStats" class="grid-datasets">
        <span v-if="historyStats.nice_size" class="mr-2">
            {{ historyStats.nice_size }}
        </span>
        <span
            v-for="(stateCount, state) of historyStats.contents_states"
            :key="state"
            :class="`stats state-color-${state}`"
            :title="`${state} datasets`">
            {{ stateCount }}
        </span>
        <span v-if="historyStats.contents_active.deleted" class="stats state-color-deleted" title="Deleted datasets">
            {{ historyStats.contents_active.deleted }}
        </span>
        <span v-if="historyStats.contents_active.hidden" class="stats state-color-hidden" title="Hidden datasets">
            {{ historyStats.contents_active.hidden }}
        </span>
    </span>
</template>

<style lang="scss" scoped>
@import "~bootstrap/scss/bootstrap.scss";
.grid-datasets {
    @extend .d-flex;
    @extend .text-nowrap;
    .stats {
        @extend .rounded;
        @extend .px-1;
        @extend .mr-1;
        border-width: 1px;
        border-style: solid;
    }
}
</style>
