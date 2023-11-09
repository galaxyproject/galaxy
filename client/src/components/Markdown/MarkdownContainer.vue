<script setup>
import { computed, ref } from "vue";

import { useConfig } from "@/composables/config";

import HistoryDatasetAsImage from "./Elements/HistoryDatasetAsImage.vue";
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

const toggle = ref(false);
const props = defineProps({
    name: {
        type: String,
        required: true,
    },
    args: {
        type: Object,
        required: true,
    },
    datasets: {
        type: Object,
        default: null,
    },
    collections: {
        type: Object,
        default: null,
    },
    histories: {
        type: Object,
        default: null,
    },
    invocations: {
        type: Object,
        default: null,
    },
    jobs: {
        type: Object,
        default: null,
    },
    time: {
        type: String,
        default: null,
    },
    version: {
        type: String,
        default: null,
    },
    workflows: {
        type: Object,
        default: null,
    },
});

const isCollapsible = computed(() => props.args.collapse !== undefined);
const isVisible = computed(() => !isCollapsible.value || toggle.value);
</script>

<template>
    <div>
        <b-link v-if="isCollapsible" class="font-weight-bold" @click="toggle = !toggle">
            {{ args.collapse }}
        </b-link>
        <b-collapse :visible="isVisible">
            <div v-if="name == 'generate_galaxy_version'" class="galaxy-version">
                <pre><code>{{ version }}</code></pre>
            </div>
            <div v-else-if="name == 'generate_time'" class="galaxy-time">
                <pre><code>{{ time }}</code></pre>
            </div>
            <div v-else-if="name == 'workflow_image'" class="workflow-image" style="text-align: center">
                <WorkflowImage :workflow-id="args.workflow_id" :size="args.size || 'lg'" />
            </div>
            <div v-else-if="name == 'workflow_license'" class="workflow-license">
                <WorkflowLicense :license-id="workflows[args.workflow_id]['license']" />
            </div>
            <InstanceUrl
                v-else-if="name == 'instance_citation_link'"
                :href="config.citation_url"
                :loading="!isConfigLoaded">
            </InstanceUrl>
            <InstanceUrl v-else-if="name == 'instance_terms_link'" :href="config.terms_url" :loading="!isConfigLoaded">
            </InstanceUrl>
            <InstanceUrl
                v-else-if="name == 'instance_support_link'"
                :href="config.support_url"
                :loading="!isConfigLoaded">
            </InstanceUrl>
            <InstanceUrl
                v-else-if="name == 'instance_help_link'"
                :href="config.helpsite_url"
                :loading="!isConfigLoaded">
            </InstanceUrl>
            <InstanceUrl
                v-else-if="name == 'instance_resources_link'"
                :href="config.instance_resource_url"
                :loading="!isConfigLoaded">
            </InstanceUrl>
            <InstanceUrl
                v-else-if="name == 'instance_access_link'"
                :href="config.instance_access_url"
                :loading="!isConfigLoaded">
            </InstanceUrl>
            <InstanceUrl
                v-else-if="name == 'instance_organization_link'"
                :href="config.ga4gh_service_organization_url"
                :title="config.ga4gh_service_organization_name"
                :loading="!isConfigLoaded">
            </InstanceUrl>
            <HistoryLink v-else-if="name == 'history_link'" :args="args" :histories="histories" />
            <HistoryDatasetAsImage v-else-if="name == 'history_dataset_as_image'" :args="args" />
            <HistoryDatasetLink v-else-if="name == 'history_dataset_link'" :args="args" />
            <HistoryDatasetIndex v-else-if="name == 'history_dataset_index'" :args="args" />
            <InvocationTime v-else-if="name == 'invocation_time'" :args="args" :invocations="invocations" />
            <JobMetrics v-else-if="name == 'job_metrics'" :args="args" />
            <JobParameters v-else-if="name == 'job_parameters'" :args="args" />
            <WorkflowDisplay
                v-else-if="name == 'workflow_display'"
                :workflow-id="args.workflow_id"
                :workflows="workflows" />
            <Visualization v-else-if="name == 'visualization'" :args="args" />
            <HistoryDatasetCollectionDisplay
                v-else-if="name == 'history_dataset_collection_display'"
                :args="args"
                :collections="collections" />
            <ToolStd v-else-if="['tool_stdout', 'tool_stderr'].includes(name)" :args="args" :name="name" :jobs="jobs" />
            <HistoryDatasetDisplay
                v-else-if="['history_dataset_embedded', 'history_dataset_display'].includes(name)"
                :args="args"
                :datasets="datasets"
                :embedded="name == 'history_dataset_embedded'" />
            <HistoryDatasetDetails
                v-else-if="
                    [
                        'history_dataset_name',
                        'history_dataset_info',
                        'history_dataset_peek',
                        'history_dataset_type',
                    ].includes(name)
                "
                :name="name"
                :args="args"
                :datasets="datasets" />
        </b-collapse>
    </div>
</template>
