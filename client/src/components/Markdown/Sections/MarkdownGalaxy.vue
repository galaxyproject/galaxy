<script setup>
import { computed, ref } from "vue";

import { getGalaxyInstance } from "@/app";
import { getArgs } from "@/components/Markdown/parse";
import { useConfig } from "@/composables/config";

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

const toggle = ref(false);
const props = defineProps({
    content: {
        type: String,
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
});

const parsedArgs = computed(() => getArgs(props.content));
const args = computed(() => parsedArgs.value.args);
const name = computed(() => parsedArgs.value.name);

const isCollapsible = computed(() => args.value.collapse !== undefined);
const isVisible = computed(() => !isCollapsible.value || toggle.value);
const version = computed(() => getGalaxyInstance().config.version_major);

function argToBoolean(args, name, booleanDefault) {
    const valueAsString = args[name];
    if (valueAsString == "true") {
        return true;
    } else if (valueAsString == "false") {
        return false;
    } else {
        return booleanDefault;
    }
}
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
                <pre><code>{{ new Date().toUTCString() }}</code></pre>
            </div>
            <div v-else-if="name == 'workflow_image'" class="workflow-image" style="text-align: center">
                <WorkflowImage
                    :workflow-id="args.workflow_id"
                    :size="args.size || 'lg'"
                    :workflow-version="args.workflow_checkpoint || undefined" />
            </div>
            <div v-else-if="name == 'workflow_license'" class="workflow-license">
                <WorkflowLicense :workflow-id="args.workflow_id" />
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
            <HistoryLink v-else-if="name == 'history_link'" :history-id="args.history_id" />
            <HistoryDatasetAsImage v-else-if="name == 'history_dataset_as_image'" :args="args" />
            <HistoryDatasetAsTable
                v-else-if="name == 'history_dataset_as_table'"
                :history-dataset-id="args.history_dataset_id"
                :compact="argToBoolean(args, 'compact', false)"
                :show-column-headers="argToBoolean(args, 'show_column_headers', true)"
                :title="args.title"
                :footer="args.footer" />
            <HistoryDatasetLink v-else-if="name == 'history_dataset_link'" :args="args" />
            <HistoryDatasetIndex v-else-if="name == 'history_dataset_index'" :args="args" />
            <InvocationTime v-else-if="name == 'invocation_time'" :invocation-id="args.invocation_id" />
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
            <WorkflowDisplay
                v-else-if="name == 'workflow_display'"
                :workflow-id="args.workflow_id"
                :workflow-version="args.workflow_checkpoint" />
            <Visualization v-else-if="name == 'visualization'" :args="args" />
            <HistoryDatasetCollectionDisplay
                v-else-if="name == 'history_dataset_collection_display'"
                :args="args"
                :collections="collections" />
            <ToolStd
                v-else-if="['tool_stdout', 'tool_stderr'].includes(name)"
                :job-id="args.job_id"
                :implicit-collection-jobs-id="args.implicit_collection_jobs_id"
                :name="name" />
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
