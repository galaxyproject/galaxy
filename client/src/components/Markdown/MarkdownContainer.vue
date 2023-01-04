<script setup>
import { computed, ref } from "vue";
import HistoryDatasetAsImage from "./Elements/HistoryDatasetAsImage.vue";
import HistoryDatasetDisplay from "./Elements/HistoryDatasetDisplay.vue";
import HistoryDatasetLink from "./Elements/HistoryDatasetLink.vue";
import HistoryDatasetIndex from "./Elements/HistoryDatasetIndex.vue";
import HistoryDatasetCollectionDisplay from "./Elements/HistoryDatasetCollection/CollectionDisplay.vue";
import HistoryDatasetDetails from "./Elements/HistoryDatasetDetails.vue";
import HistoryLink from "./Elements/HistoryLink.vue";
import InvocationTime from "./Elements/InvocationTime.vue";
import JobMetrics from "./Elements/JobMetrics.vue";
import JobParameters from "./Elements/JobParameters.vue";
import ToolStd from "./Elements/ToolStd.vue";
import WorkflowDisplay from "./Elements/Workflow/WorkflowDisplay.vue";
import Visualization from "./Elements/Visualization.vue";

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
            <HistoryLink v-else-if="name == 'history_link'" :args="args" :histories="histories" />
            <HistoryDatasetAsImage v-else-if="name == 'history_dataset_as_image'" :args="args" />
            <HistoryDatasetLink v-else-if="name == 'history_dataset_link'" :args="args" />
            <HistoryDatasetIndex v-else-if="name == 'history_dataset_index'" :args="args" />
            <InvocationTime v-else-if="name == 'invocation_time'" :args="args" :invocations="invocations" />
            <JobMetrics v-else-if="name == 'job_metrics'" :args="args" />
            <JobParameters v-else-if="name == 'job_parameters'" :args="args" />
            <WorkflowDisplay v-else-if="name == 'workflow_display'" :args="args" :workflows="workflows" />
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
