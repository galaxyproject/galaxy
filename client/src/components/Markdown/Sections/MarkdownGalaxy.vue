<script setup>
import axios from "axios";
import { computed, ref, watch } from "vue";

import { getGalaxyInstance } from "@/app";
import { getArgs } from "@/components/Markdown/parse";
import { useConfig } from "@/composables/config";
import { getAppRoot } from "@/onload/loadConfig";

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

const { config, isConfigLoaded } = useConfig();

const props = defineProps({
    content: {
        type: String,
        required: true,
    },
});

const args = ref();
const attributes = ref();
const error = ref("");
const loaded = ref(false);
const toggle = ref(false);

const isCollapsible = computed(() => args.value.collapse !== undefined);
const isVisible = computed(() => !isCollapsible.value || toggle.value);
const name = computed(() => attributes.value.name);
const version = computed(() => getGalaxyInstance().config.version_major);

async function handleArgs() {
    try {
        error.value = "";
        attributes.value = getArgs(props.content);
        const attributesArgs = { ...attributes.value.args };

        if (attributesArgs.invocation_id) {
            if (attributesArgs.output) {
                console.log(attributesArgs.invocation_id);
            }
            const { data: invocation } = await axios.get(
                `${getAppRoot()}api/invocations/${attributesArgs.invocation_id}`
            );
            if (invocation) {
                attributesArgs.invocation = invocation;
                if (attributesArgs.input && invocation.inputs) {
                    const inputValues = Object.values(invocation.inputs);
                    const input = inputValues.find((i) => i.label === attributesArgs.input);
                    attributesArgs.history_target_id = input?.id;
                } else if (attributesArgs.output && invocation.outputs) {
                    const targetId = invocation.outputs[attributesArgs.output]?.id || "";
                    attributesArgs.history_target_id = targetId;
                } else if (attributesArgs.step && invocation.steps) {
                    const step = invocation.steps.find((s) => s.workflow_step_label === attributesArgs.step);
                    attributesArgs.job_id = step?.job_id;
                    attributesArgs.implicit_collection_jobs_id = step?.implicit_collection_jobs_id;
                }
            } else {
                error.value = "Failed to retrieve invocation.";
            }
        }
        args.value = attributesArgs;
    } catch (e) {
        error.value = "The directive provided below is invalid. Please review it for errors.";
        attributes.value = {};
    }
    loaded.value = true;
}

watch(
    () => props.content,
    () => {
        handleArgs();
    },
    { immediate: true }
);
</script>

<template>
    <div v-if="loaded">
        <b-alert v-if="error" variant="danger" show>
            {{ error }}
        </b-alert>
        <b-link v-if="isCollapsible" class="font-weight-bold" @click="toggle = !toggle">
            {{ args.collapse }}
        </b-link>
        <b-collapse :visible="isVisible">
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
        </b-collapse>
    </div>
</template>
