<script setup>
import { BAlert, BCollapse, BLink } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { getArgs } from "@/components/Markdown/parse";
import { parseInvocation } from "@/components/Markdown/Utilities/parseInvocation";
import { useConfig } from "@/composables/config";
import { useInvocationStore } from "@/stores/invocationStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import HistoryDatasetAsImage from "./Elements/HistoryDatasetAsImage.vue";
import HistoryDatasetAsTable from "./Elements/HistoryDatasetAsTable.vue";
import HistoryDatasetCollectionDisplay from "./Elements/HistoryDatasetCollection/CollectionDisplay.vue";
import HistoryDatasetDetails from "./Elements/HistoryDatasetDetails.vue";
import HistoryDatasetDisplay from "./Elements/HistoryDatasetDisplay.vue";
import HistoryDatasetIndex from "./Elements/HistoryDatasetIndex.vue";
import HistoryDatasetLink from "./Elements/HistoryDatasetLink.vue";
import HistoryLink from "./Elements/HistoryLink.vue";
import InstanceUrl from "./Elements/InstanceUrl.vue";
import InvocationTime from "./Elements/InvocationTime.vue";
import JobMetrics from "./Elements/JobMetrics.vue";
import JobParameters from "./Elements/JobParameters.vue";
import ToolStd from "./Elements/ToolStd.vue";
import Visualization from "./Elements/Visualization.vue";
import WorkflowDisplay from "./Elements/Workflow/WorkflowDisplay.vue";
import WorkflowImage from "./Elements/Workflow/WorkflowImage.vue";
import WorkflowLicense from "./Elements/Workflow/WorkflowLicense.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const { config, isConfigLoaded } = useConfig();
const { getInvocationById, getInvocationLoadError, isLoadingInvocation } = useInvocationStore();
const { fetchWorkflowForInstanceIdCached, getStoredWorkflowIdByInstanceId } = useWorkflowStore();

const props = defineProps({
    content: {
        type: String,
        required: true,
    },
});

const attributes = ref({});
const error = ref("");
const toggle = ref(false);
const workflowLoading = ref(false);

const args = computed(() => {
    if (invocation.value && workflowId.value) {
        return parseInvocation(invocation.value, workflowId.value, name.value, attributes.value.args);
    } else {
        return { ...attributes.value.args };
    }
});

const invocation = computed(() => invocationId.value && getInvocationById(invocationId.value));
const invocationId = computed(() => attributes.value.args?.invocation_id);
const invocationLoading = computed(() => isLoadingInvocation(invocationId.value));
const invocationLoadError = computed(() => getInvocationLoadError(invocationId.value));
const isCollapsible = computed(() => args.value?.collapse !== undefined);
const isLoading = computed(() => invocationLoading.value || workflowLoading.value);
const isVisible = computed(() => !isCollapsible.value || toggle.value);
const name = computed(() => attributes.value.name);
const version = computed(() => config.version_major);
const workflowId = computed(() => invocation.value && getStoredWorkflowIdByInstanceId(invocation.value.workflow_id));

async function fetchWorkflow() {
    if (invocation.value?.workflow_id) {
        try {
            workflowLoading.value = true;
            await fetchWorkflowForInstanceIdCached(invocation.value.workflow_id);
        } catch (e) {
            error.value = String(e);
        } finally {
            workflowLoading.value = false;
        }
    }
}

function handleAttributes() {
    try {
        error.value = "";
        attributes.value = getArgs(props.content);
    } catch (e) {
        error.value = "The directive provided below is invalid. Please review it for errors.";
        attributes.value = {};
    }
}

watch(
    () => props.content,
    () => handleAttributes(),
    { immediate: true }
);

watch(
    () => invocation.value,
    () => fetchWorkflow(),
    { immediate: true }
);
</script>

<template>
    <BAlert v-if="error" v-localize variant="danger" show>
        {{ error }}
    </BAlert>
    <BAlert v-else-if="invocationLoadError" v-localize variant="danger" show>
        {{ invocationLoadError }}
    </BAlert>
    <LoadingSpan v-else-if="isLoading" />
    <div v-else>
        <BLink v-if="isCollapsible" class="font-weight-bold" @click="toggle = !toggle">
            {{ args.collapse }}
        </BLink>
        <BCollapse :visible="isVisible">
            <div v-if="name == 'generate_galaxy_version'" class="galaxy-version">
                <pre><code>{{ version }}</code></pre>
            </div>
            <div v-else-if="name == 'generate_time'" class="galaxy-time">
                <pre><code>{{ new Date().toUTCString() }}</code></pre>
            </div>
            <HistoryDatasetAsImage
                v-else-if="name == 'history_dataset_as_image'"
                :dataset-id="args.history_target_id || args.history_dataset_id"
                :path="args.path" />
            <HistoryDatasetAsTable
                v-else-if="name == 'history_dataset_as_table'"
                :compact="argToBoolean(args, 'compact', false)"
                :dataset-id="args.history_target_id || args.history_dataset_id"
                :footer="args.footer"
                :show-column-headers="argToBoolean(args, 'show_column_headers', true)"
                :title="args.title" />
            <HistoryDatasetCollectionDisplay
                v-else-if="name == 'history_dataset_collection_display'"
                :collection-id="args.history_target_id || args.history_dataset_collection_id" />
            <HistoryDatasetDetails
                v-else-if="
                    [
                        'history_dataset_name',
                        'history_dataset_info',
                        'history_dataset_peek',
                        'history_dataset_type',
                    ].includes(name)
                "
                :dataset-id="args.history_target_id || args.history_dataset_id"
                :name="name" />
            <HistoryDatasetDisplay
                v-else-if="['history_dataset_embedded', 'history_dataset_display'].includes(name)"
                :dataset-id="args.history_target_id || args.history_dataset_id"
                :embedded="name == 'history_dataset_embedded'" />
            <HistoryDatasetIndex v-else-if="name == 'history_dataset_index'" :args="args" />
            <HistoryDatasetLink v-else-if="name == 'history_dataset_link'" :args="args" />
            <HistoryLink v-else-if="name == 'history_link'" :history-id="args.history_id" />
            <InstanceUrl
                v-else-if="name == 'instance_access_link'"
                :href="config.instance_access_url"
                :loading="!isConfigLoaded" />
            <InstanceUrl
                v-else-if="name == 'instance_citation_link'"
                :href="config.citation_url"
                :loading="!isConfigLoaded" />
            <InstanceUrl
                v-else-if="name == 'instance_help_link'"
                :href="config.helpsite_url"
                :loading="!isConfigLoaded" />
            <InstanceUrl
                v-else-if="name == 'instance_organization_link'"
                :href="config.ga4gh_service_organization_url"
                :title="config.ga4gh_service_organization_name"
                :loading="!isConfigLoaded" />
            <InstanceUrl
                v-else-if="name == 'instance_resources_link'"
                :href="config.instance_resource_url"
                :loading="!isConfigLoaded" />
            <InstanceUrl
                v-else-if="name == 'instance_support_link'"
                :href="config.support_url"
                :loading="!isConfigLoaded" />
            <InstanceUrl
                v-else-if="name == 'instance_terms_link'"
                :href="config.terms_url"
                :loading="!isConfigLoaded" />
            <InvocationTime v-else-if="name == 'invocation_time'" :invocation-id="args.invocation_id" />
            <div v-else-if="name === 'invocation_inputs'">
                <div v-for="(input, index) in args.invocation.inputs" :key="index">
                    <h4>Input {{ parseInt(index) + 1 }}: {{ input.label }}</h4>
                </div>
            </div>
            <div v-else-if="name === 'invocation_outputs'">
                <div v-for="(outputKey, index) in Object.keys(args.invocation.outputs)" :key="index">
                    <h4>Output {{ index + 1 }}: {{ outputKey }}</h4>
                </div>
            </div>
            <JobMetrics
                v-else-if="name == 'job_metrics'"
                :job-id="args.job_id"
                :implicit-collection-jobs-id="args.implicit_collection_jobs_id"
                :title="args.title"
                :footer="args.footer" />
            <JobParameters
                v-else-if="name == 'job_parameters'"
                :job-id="args.job_id"
                :implicit-collection-jobs-id="args.implicit_collection_jobs_id"
                :param="args.param || undefined"
                :title="args.title"
                :footer="args.footer" />
            <ToolStd
                v-else-if="['tool_stdout', 'tool_stderr'].includes(name)"
                :job-id="args.job_id"
                :implicit-collection-jobs-id="args.implicit_collection_jobs_id"
                :name="name" />
            <Visualization v-else-if="name == 'visualization'" :args="args" />
            <WorkflowDisplay
                v-else-if="name == 'workflow_display'"
                :workflow-id="args.workflow_id"
                :workflow-version="args.workflow_checkpoint" />
            <WorkflowImage
                v-else-if="name == 'workflow_image'"
                :workflow-id="args.workflow_id"
                :size="args.size || 'lg'"
                :workflow-version="args.workflow_checkpoint || undefined" />
            <WorkflowLicense v-else-if="name == 'workflow_license'" :workflow-id="args.workflow_id" />
        </BCollapse>
    </div>
</template>
