<template>
    <div>
        <b-link v-if="isCollapsible" class="font-weight-bold" @click="toggle = !toggle">
            {{ obj.args.collapse }}
        </b-link>
        <b-collapse :visible="isVisible">
            <div v-if="obj.name == 'generate_galaxy_version'" class="galaxy-version">
                <pre><code>{{ getVersion }}</code></pre>
            </div>
            <div v-else-if="obj.name == 'generate_time'" class="galaxy-time">
                <pre><code>{{ getTime }}</code></pre>
            </div>
            <HistoryLink v-else-if="obj.name == 'history_link'" :args="obj.args" :histories="histories" />
            <HistoryDatasetAsImage v-else-if="obj.name == 'history_dataset_as_image'" :args="obj.args" />
            <HistoryDatasetLink v-else-if="obj.name == 'history_dataset_link'" :args="obj.args" />
            <HistoryDatasetIndex v-else-if="obj.name == 'history_dataset_index'" :args="obj.args" />
            <InvocationTime v-else-if="obj.name == 'invocation_time'" :args="obj.args" :invocations="invocations" />
            <JobMetrics v-else-if="obj.name == 'job_metrics'" :args="obj.args" />
            <JobParameters v-else-if="obj.name == 'job_parameters'" :args="obj.args" />
            <WorkflowDisplay v-else-if="obj.name == 'workflow_display'" :args="obj.args" :workflows="workflows" />
            <Visualization v-else-if="obj.name == 'visualization'" :args="obj.args" />
            <HistoryDatasetCollectionDisplay
                v-else-if="obj.name == 'history_dataset_collection_display'"
                :args="obj.args"
                :collections="collections" />
            <ToolStd
                v-else-if="['tool_stdout', 'tool_stderr'].includes(obj.name)"
                :args="obj.args"
                :name="obj.name"
                :jobs="jobs" />
            <HistoryDatasetDisplay
                v-else-if="['history_dataset_embedded', 'history_dataset_display'].includes(obj.name)"
                :args="obj.args"
                :datasets="datasets"
                :embedded="obj.name == 'history_dataset_embedded'" />
            <HistoryDatasetDetails
                v-else-if="
                    ['history_dataset_name', 'history_dataset_info', 'history_dataset_peek', 'history_dataset_type'].includes(
                        obj.name
                    )
                "
                :name="obj.name"
                :args="obj.args"
                :datasets="datasets" />
        </b-collapse>
    </div>
</template>

<script>
import HistoryDatasetAsImage from "./Elements/HistoryDatasetAsImage";
import HistoryDatasetDisplay from "./Elements/HistoryDatasetDisplay";
import HistoryDatasetLink from "./Elements/HistoryDatasetLink";
import HistoryDatasetIndex from "./Elements/HistoryDatasetIndex";
import HistoryDatasetCollectionDisplay from "./Elements/HistoryDatasetCollection/CollectionDisplay";
import HistoryDatasetDetails from "./Elements/HistoryDatasetDetails";
import HistoryLink from "./Elements/HistoryLink";
import InvocationTime from "./Elements/InvocationTime";
import JobMetrics from "./Elements/JobMetrics";
import JobParameters from "./Elements/JobParameters";
import ToolStd from "./Elements/ToolStd";
import WorkflowDisplay from "./Elements/Workflow/WorkflowDisplay";
import Visualization from "./Elements/Visualization";
export default {
    components: {
        HistoryDatasetDetails,
        HistoryDatasetAsImage,
        HistoryDatasetCollectionDisplay,
        HistoryDatasetDisplay,
        HistoryDatasetIndex,
        HistoryDatasetLink,
        HistoryLink,
        InvocationTime,
        JobMetrics,
        JobParameters,
        WorkflowDisplay,
        ToolStd,
        Visualization,
    },
    props: {
        obj: {
            type: Object,
            default: null,
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
        workflows: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            toggle: false,
        };
    },
    computed: {
        isVisible() {
            return !this.isCollapsible || this.toggle;
        },
        isCollapsible() {
            return this.obj.args.collapse !== undefined;
        },
    },
};
</script>
