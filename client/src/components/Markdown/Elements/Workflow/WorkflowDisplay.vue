<script setup lang="ts">
import axios from "axios";
import { computed, ref, onMounted } from "vue";
import { withPrefix } from "@/utils/redirect";
import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowTree from "./WorkflowTree.vue";

interface WorkflowDisplayProps {
    workflowId: string;
    embedded?: boolean;
    expanded?: boolean;
}

const props = withDefaults(defineProps<WorkflowDisplayProps>(), {
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
const itemUrl = computed(() => withPrefix(`/api/workflows/${props.workflowId}/download?style=preview`));

onMounted(async () => {
    axios
        .get(itemUrl.value)
        .then((response) => {
            itemContent.value = response.data;
            loading.value = false;
        })
        .catch((error) => {
            errorContent.value = error.response.data.err_msg;
            loading.value = false;
        });
});
</script>

<template>
    <b-card body-class="p-0">
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
                    <span class="fa fa-file-import" />
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
                <b-alert v-if="errorContent !== null" variant="danger" show>
                    <b>Please fix the following error(s):</b>
                    <ul v-if="typeof errorContent === 'object'" class="my-2">
                        <li v-for="(errorValue, errorKey) in errorContent" :key="errorKey">
                            {{ errorKey }}: {{ errorValue }}
                        </li>
                    </ul>
                    <div v-else>{{ errorContent }}</div>
                </b-alert>
                <div v-if="itemContent !== null">
                    <div v-for="step in itemContent?.steps" :key="step.order_index" class="mb-2">
                        <div>Step {{ step.order_index + 1 }}: {{ step.label }}</div>
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
