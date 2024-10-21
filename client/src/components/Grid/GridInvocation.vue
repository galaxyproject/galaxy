<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import invocationsGridConfig from "@/components/Grid/configs/invocations";
import invocationsHistoryGridConfig from "@/components/Grid/configs/invocationsHistory";
import invocationsWorkflowGridConfig from "@/components/Grid/configs/invocationsWorkflow";
import { useUserStore } from "@/stores/userStore";

import type { GridConfig } from "./configs/types";

import Heading from "../Common/Heading.vue";
import UtcDate from "../UtcDate.vue";
import WorkflowInvocationState from "../WorkflowInvocationState/WorkflowInvocationState.vue";
import GridList from "@/components/Grid/GridList.vue";

interface Props {
    noInvocationsMessage?: string;
    headerMessage?: string;
    ownerGrid?: boolean;
    filteredFor?: { type: "History" | "StoredWorkflow"; id: string; name: string };
}

const props = withDefaults(defineProps<Props>(), {
    noInvocationsMessage: "No Workflow Invocations to display",
    headerMessage: "",
    ownerGrid: true,
    filteredFor: undefined,
});

const { currentUser } = storeToRefs(useUserStore());

const forStoredWorkflow = computed(() => props.filteredFor?.type === "StoredWorkflow");
const forHistory = computed(() => props.filteredFor?.type === "History");

const effectiveNoInvocationsMessage = computed(() => {
    let message = props.noInvocationsMessage;
    if (props.filteredFor) {
        message += ` for ${props.filteredFor?.name}`;
    }
    return message;
});

const effectiveTitle = computed(() => {
    let retVal = `Workflow Invocations`;
    const type = props.filteredFor?.type === "StoredWorkflow" ? "Workflow" : "History";
    if (props.filteredFor && props.filteredFor?.name) {
        retVal += ` for ${type} "${props.filteredFor.name}"`;
    }
    return retVal;
});

const extraProps = computed(() => {
    const params: {
        workflow_id?: string;
        history_id?: string;
        include_terminal?: boolean;
        user_id?: string;
    } = {};
    if (forStoredWorkflow.value) {
        params.workflow_id = props.filteredFor?.id;
    }
    if (forHistory.value) {
        params.history_id = props.filteredFor?.id;
    }
    if (!props.ownerGrid) {
        params.include_terminal = false;
    } else if (currentUser.value && !currentUser.value?.isAnonymous) {
        params.user_id = currentUser.value?.id;
    }
    return params;
});

let gridConfig: GridConfig;
if (forStoredWorkflow.value) {
    gridConfig = invocationsWorkflowGridConfig;
} else if (forHistory.value) {
    gridConfig = invocationsHistoryGridConfig;
} else {
    gridConfig = invocationsGridConfig;
}

function refreshTable() {
    // TODO: Implement
}
</script>

<template>
    <div class="d-flex flex-column">
        <div v-if="forStoredWorkflow || forHistory" class="d-flex">
            <Heading h1 separator inline truncate size="xl" class="flex-grow-1 mb-2">{{ effectiveTitle }}</Heading>
        </div>
        <GridList
            v-if="!currentUser?.isAnonymous && currentUser?.id"
            class="grid-invocation"
            :grid-config="gridConfig"
            :grid-message="props.headerMessage"
            :no-data-message="effectiveNoInvocationsMessage"
            :extra-props="extraProps"
            :embedded="forStoredWorkflow || forHistory">
            <template v-slot:expanded="{ rowData }">
                <span class="float-right position-absolute mr-4" style="right: 0" :data-invocation-id="rowData.id">
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
