<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import type { FetchTargets } from "@/api/tools";
import { useToolLandingStore } from "@/stores/toolLandingStore";

import FetchLanding from "./FetchLanding.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    uuid: string;
    secret?: string;
    public?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    secret: undefined,
    public: false,
});

const store = useToolLandingStore();
const { claimTool } = store;
const { claimState } = storeToRefs(store);

// Start claim immediately
claimTool(props.uuid, props.public, props.secret).then(() => {
    console.debug("tool request claimed");
});

interface DataFetchRequestState {
    request_json: {
        targets: FetchTargets;
    };
}

const fetchTargets = computed<FetchTargets | null>(() => {
    const requestState = claimState.value.requestState;
    if (requestState) {
        const targets = (requestState as unknown as DataFetchRequestState).request_json.targets;
        return targets;
    } else {
        return null;
    }
});
</script>

<template>
    <div>
        <div v-if="claimState.errorMessage">
            <BAlert variant="danger" show>
                {{ claimState.errorMessage }}
            </BAlert>
        </div>
        <div v-else-if="!claimState.toolId">
            <LoadingSpan message="Loading tool parameters" />
        </div>
        <div v-else-if="claimState.toolId == '__DATA_FETCH__' && fetchTargets" class="h-100">
            <FetchLanding :targets="fetchTargets" :landing-uuid="props.uuid" />
        </div>
        <div v-else>
            {{ claimState.requestState }}
        </div>
    </div>
</template>
