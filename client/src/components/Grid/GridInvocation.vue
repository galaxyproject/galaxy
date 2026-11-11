<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import type { WorkflowInvocation } from "@/api/invocations";
import invocationsBatchConfig from "@/components/Grid/configs/invocationsBatch";
import { useUserStore } from "@/stores/userStore";

import UtcDate from "../UtcDate.vue";
import WorkflowInvocationState from "../WorkflowInvocationState/WorkflowInvocationState.vue";
import GridList from "@/components/Grid/GridList.vue";

interface Props {
    invocationsList: WorkflowInvocation[];
}

const props = defineProps<Props>();

const { currentUser } = storeToRefs(useUserStore());

const extraProps = computed(() =>
    Object.fromEntries(props.invocationsList.map((invocation) => [invocation.id, invocation])),
);

function refreshTable() {
    // TODO: Implement
}
</script>

<template>
    <div class="d-flex flex-column">
        <GridList
            v-if="!currentUser?.isAnonymous && currentUser?.id"
            class="grid-invocation"
            :grid-config="invocationsBatchConfig"
            no-data-message="No Workflow Invocations to display"
            :extra-props="extraProps"
            embedded>
            <template v-slot:expanded="{ rowData }">
                <span class="mb-2" :data-invocation-id="rowData.id">
                    <small>
                        <b>Last updated: <UtcDate :date="rowData.update_time" mode="elapsed" />; Invocation ID:</b>
                    </small>
                    <code>{{ rowData.id }}</code>
                </span>
                <WorkflowInvocationState :invocation-id="rowData.id" @invocation-cancelled="refreshTable" />
            </template>
        </GridList>
    </div>
</template>

<style scoped lang="scss">
.grid-invocation {
    // prevent steps & zoom (within rowDetails) from overlapping header and footer
    &:deep(.grid-header) {
        z-index: 100;
    }
    &:deep(.grid-footer) {
        z-index: 100;
    }
    &:deep(.flex-panel.right) {
        z-index: 50;
    }
    &:deep(.zoom-control) {
        z-index: 50;
    }
}
</style>
