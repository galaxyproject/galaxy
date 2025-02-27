<script setup lang="ts">
import axios from "axios";
import { computed, ref, watch } from "vue";

import { withPrefix } from "@/utils/redirect";
import { isEmpty } from "@/utils/utils";

import WorkflowTree from "./WorkflowTree.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ToolLinkPopover from "@/components/Tool/ToolLinkPopover.vue";
import WorkflowStepIcon from "@/components/WorkflowInvocationState/WorkflowStepIcon.vue";
import WorkflowStepTitle from "@/components/WorkflowInvocationState/WorkflowStepTitle.vue";

interface WorkflowDisplayProps {
    workflowId: string;
    workflowVersion?: string;
    embedded?: boolean;
    expanded?: boolean;
}

const props = withDefaults(defineProps<WorkflowDisplayProps>(), {
    workflowVersion: undefined,
    embedded: false,
    expanded: false,
});

type ItemContent = {
    name: string;
    steps: Array<any>; // This isn't actually a proper workflow step type, right?  TODO, unify w/ workflowStepStore?
};

const errorContent = ref();
const itemContent = ref<ItemContent | null>(null);
const loading = ref(true);

const workflowName = computed(() => (itemContent.value ? itemContent.value.name : "..."));
const downloadUrl = computed(() => withPrefix(`/api/workflows/${props.workflowId}/download?format=json-download`));
const importUrl = computed(() => withPrefix(`/workflow/imp?id=${props.workflowId}`));
const itemUrl = computed(() => {
    let extra = "";
    if (props.workflowVersion) {
        extra = `&version=${props.workflowVersion}`;
    }
    return withPrefix(`/api/workflows/${props.workflowId}/download?style=preview${extra}`);
});

watch(
    () => props.workflowId,
    () => {
        loading.value = true;
        if (props.workflowId) {
            axios
                .get(itemUrl.value)
                .then((response) => {
                    errorContent.value = null;
                    itemContent.value = response.data;
                    loading.value = false;
                })
                .catch((error) => {
                    errorContent.value = error.response.data.err_msg;
                    itemContent.value = null;
                    loading.value = false;
                });
        } else {
            errorContent.value = "Workflow id is missing.";
            itemContent.value = null;
            loading.value = false;
        }
    },
    { immediate: true }
);
</script>

<template>
    <b-alert v-if="!isEmpty(errorContent)" variant="warning" show>
        <ul v-if="typeof errorContent === 'object'" class="my-2">
            <li v-for="(errorValue, errorKey) in errorContent" :key="errorKey">{{ errorKey }}: {{ errorValue }}</li>
        </ul>
        <div v-else>{{ errorContent }}</div>
    </b-alert>
    <b-card v-else body-class="p-0" class="workflow-display">
        <b-card-header v-if="!embedded">
            <span class="float-right">
                <b-button
                    v-b-tooltip.hover
                    :href="downloadUrl"
                    variant="link"
                    size="sm"
                    role="button"
                    title="Download Workflow"
                    type="button"
                    class="py-0 px-1"
                    data-description="workflow download">
                    <span class="fa fa-download" />
                </b-button>
                <b-button
                    v-b-tooltip.hover
                    :href="importUrl"
                    role="button"
                    variant="link"
                    title="Import Workflow"
                    type="button"
                    class="py-0 px-1"
                    data-description="workflow import">
                    <span class="fa fa-upload" />
                </b-button>
            </span>
            <span>
                <span>Workflow:</span>
                <span class="font-weight-light" data-description="workflow name">{{ workflowName }}</span>
            </span>
        </b-card-header>
        <b-card-body>
            <LoadingSpan v-if="loading" message="Loading Workflow" />
            <div v-else :class="!expanded && 'content-height'">
                <div v-if="itemContent !== null">
                    <div v-for="step in itemContent?.steps" :key="step.order_index" class="mb-2">
                        <span :id="`step-icon-${step.order_index}`">
                            <WorkflowStepIcon v-if="step.type" :step-type="step.type" />
                        </span>
                        <ToolLinkPopover
                            v-if="step.type == 'tool'"
                            :target="`step-icon-${step.order_index}`"
                            :tool-id="step.tool_id"
                            :tool-version="step.tool_version" />
                        <WorkflowStepTitle
                            :step-tool-id="step.tool_id"
                            :step-subworkflow-id="step.subworkflow_id"
                            :step-label="step.label"
                            :step-type="step.type"
                            :step-index="step.order_index" />
                        <WorkflowTree :input="step" :skip-head="true" />
                    </div>
                </div>
            </div>
        </b-card-body>
    </b-card>
</template>
<style scoped>
.content-height {
    max-height: 15rem;
    overflow-y: auto;
}
</style>
