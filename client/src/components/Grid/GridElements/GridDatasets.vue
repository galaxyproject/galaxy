<script setup lang="ts">
import axios from "axios";
import { onMounted, type Ref,ref } from "vue";

import { withPrefix } from "@/utils/redirect";

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
        ok?: number;
        running?: number;
        queued?: number;
        new?: number;
    }
}
const historyStats: Ref<HistoryStats | null> = ref(null);

const states = ["error", "new", "ok", "running", "queued"];
const active = ["active", "deleted", "hidden"];

async function getCounts() {
    if (props.historyId) {
        try {
            const { data } = await axios.get(withPrefix(`/api/histories/${props.historyId}?keys=nice_size,contents_active,contents_states`));
            historyStats.value = data;
        } catch(e) {

        }
    }
}

onMounted(() => {
    getCounts();
});
</script>

<template>
    <span v-if="historyStats">
        <span v-if="historyStats.nice_size" class="mr-3">
            {{ historyStats.nice_size }}
        </span>
        <span v-if="historyStats.contents_states">
            <span v-for="(stateCount, state) of historyStats.contents_states"
                :class="`count-box state-color-${state}`"
                :title="`Datasets in ${state}`" >
                    {{ stateCount }}
            </span>
        </span>
        <span v-if="historyStats.contents_states">
            <span v-if="historyStats.contents_active.deleted" class="count-box state-color-deleted" title="Deleted datasets">{{ historyStats.contents_active.deleted }} </span>
            <span v-if="historyStats.contents_active.hidden" class="count-box state-color-hidden" title="Hidden datasets"> {{ historyStats.contents_active.hidden }}</span>
        </span>
    </span>
</template>

<style lang="scss">
.count-box {
    min-width: 1.1em;
    padding: 5px;
    border-width: 1px;
    border-style: solid;
    text-align: center;
    display: inline-block;
}
</style>