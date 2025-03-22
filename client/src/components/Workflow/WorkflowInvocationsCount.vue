<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faList } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { onMounted, ref } from "vue";

import { GalaxyApi } from "@/api";
import localize from "@/utils/localization";
import { rethrowSimple } from "@/utils/simple-error";

library.add(faList);

interface Props {
    workflow: any;
}

const props = defineProps<Props>();

const count = ref<number | undefined>(undefined);

async function initCounts() {
    const { data, error } = await GalaxyApi().GET("/api/workflows/{workflow_id}/counts", {
        params: { path: { workflow_id: props.workflow.id } },
    });

    if (error) {
        rethrowSimple(error);
    }

    let allCounts = 0;
    for (const stateCount of Object.values(data)) {
        if (stateCount) {
            allCounts += stateCount;
        }
    }
    count.value = allCounts;
}

onMounted(initCounts);
</script>

<template>
    <div class="workflow-invocations-count d-flex align-items-center flex-gapx-1">
        <BBadge v-if="count != undefined && count === 0" pill>
            <FontAwesomeIcon :icon="faList" fixed-width />
            <span>never run</span>
        </BBadge>
        <BBadge
            v-else-if="count != undefined && count > 0"
            v-b-tooltip.hover.noninteractive
            pill
            :title="localize('View workflow invocations')"
            class="outline-badge cursor-pointer"
            :to="`/workflows/${props.workflow.id}/invocations`">
            <FontAwesomeIcon :icon="faList" fixed-width />

            <span>
                workflow runs:
                {{ count }}
            </span>
        </BBadge>
        <BButton
            v-else
            v-b-tooltip.hover.noninteractive
            :title="localize('View workflow invocations')"
            class="inline-icon-button"
            variant="link"
            size="sm"
            :to="`/workflows/${props.workflow.id}/invocations`">
            <FontAwesomeIcon :icon="faList" fixed-width />
        </BButton>
    </div>
</template>
