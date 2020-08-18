<template>
    <div class="markdown-wrapper">
        <LoadingSpan v-if="loading" />
        <div v-else>
            <a v-if="effectiveExportLink" :href="exportLink" class="markdown-export position-absolute p-3">
                <i class="fa fa-3x fa-download" />
            </a>
            <div>
                <h3 class="float-right align-middle mr-1 mt-2">Galaxy {{ markdownConfig.model_class }}</h3>
                <span class="float-left font-weight-light mb-3">
                    <small>Title: {{ markdownConfig.title || markdownConfig.model_class }}</small
                    ><br />
                    <small>Username: {{ markdownConfig.username }}</small>
                </span>
            </div>
            <b-badge variant="info" class="w-100 rounded mb-3">
                <div class="float-left m-1">Created with Galaxy {{ getVersion }} on {{ getTime }} UTC</div>
                <div class="float-right m-1">Identifier {{ markdownConfig.id }}</div>
            </b-badge>
            <div v-html="markdownRendered"></div>
            <div v-for="obj in markdownObjects" :key="obj.key">
                <div v-if="obj.name == 'generate_galaxy_version'" class="galaxy-version">
                    <pre><code>{{ getVersion }}</code></pre>
                </div>
                <div v-else-if="obj.name == 'generate_time'" class="galaxy-time">
                    <pre><code>{{ getTime }}</code></pre>
                </div>
                <HistoryDatasetAsImage v-else-if="obj.name == 'history_dataset_as_image'" :args="obj.args" />
                <HistoryDatasetLink v-else-if="obj.name == 'history_dataset_link'" :args="obj.args" />
                <HistoryDatasetIndex v-else-if="obj.name == 'history_dataset_index'" :args="obj.args" />
                <InvocationTime v-else-if="obj.name == 'invocation_time'" :args="obj.args" :invocations="invocations" />
                <JobMetrics v-else-if="obj.name == 'job_metrics'" :args="obj.args" />
                <JobParameters v-else-if="obj.name == 'job_parameters'" :args="obj.args" />
                <WorkflowDisplay v-else-if="obj.name == 'workflow_display'" :args="obj.args" :workflows="workflows" />
                <HistoryDatasetCollectionDisplay
                    v-else-if="obj.name == 'history_dataset_collection_display'"
                    :args="obj.args"
                    :collections="historyDatasetCollections"
                />
                <ToolStd
                    v-else-if="['tool_stdout', 'tool_stderr'].includes(obj.name)"
                    :args="obj.args"
                    :name="obj.name"
                    :jobs="jobs"
                />
                <HistoryDatasetDisplay
                    v-else-if="['history_dataset_embedded', 'history_dataset_display'].includes(obj.name)"
                    :args="obj.args"
                    :datasets="historyDatasets"
                    :embedded="obj.name == 'history_dataset_embedded'"
                />
                <HistoryDatasetDetails
                    v-else-if="
                        [
                            'history_dataset_name',
                            'history_dataset_info',
                            'history_dataset_peek',
                            'history_dataset_type',
                        ].includes(obj.name)
                    "
                    :name="obj.name"
                    :args="obj.args"
                    :datasets="historyDatasets"
                />
                <br />
            </div>
        </div>
    </div>
</template>

<script>
import store from "store";
import { getGalaxyInstance } from "app";
import MarkdownIt from "markdown-it";
import LoadingSpan from "components/LoadingSpan";

import HistoryDatasetAsImage from "./Elements/HistoryDatasetAsImage";
import HistoryDatasetDisplay from "./Elements/HistoryDatasetDisplay";
import HistoryDatasetLink from "./Elements/HistoryDatasetLink";
import HistoryDatasetIndex from "./Elements/HistoryDatasetIndex";
import HistoryDatasetCollectionDisplay from "./Elements/HistoryDatasetCollection/CollectionDisplay";
import HistoryDatasetDetails from "./Elements/HistoryDatasetDetails";
import InvocationTime from "./Elements/InvocationTime";
import JobMetrics from "./Elements/JobMetrics";
import JobParameters from "./Elements/JobParameters";
import ToolStd from "./Elements/ToolStd";
import WorkflowDisplay from "./Elements/Workflow/WorkflowDisplay";

const FUNCTION_VALUE_REGEX = `\\s*(?:[\\w_\\-]+|\\"[^\\"]+\\"|\\'[^\\']+\\')\\s*`;
const FUNCTION_CALL = `\\s*\\w+\\s*=` + FUNCTION_VALUE_REGEX;
const FUNCTION_CALL_LINE = `\\s*(\\w+)\\s*\\(\\s*(?:(${FUNCTION_CALL})(,${FUNCTION_CALL})*)?\\s*\\)\\s*`;
const FUNCTION_CALL_LINE_TEMPLATE = new RegExp(FUNCTION_CALL_LINE, "m");

const md = MarkdownIt();

const default_fence = md.renderer.rules.fence;

export default {
    store: store,
    components: {
        HistoryDatasetDetails,
        HistoryDatasetAsImage,
        HistoryDatasetCollectionDisplay,
        HistoryDatasetDisplay,
        HistoryDatasetIndex,
        HistoryDatasetLink,
        JobMetrics,
        JobParameters,
        LoadingSpan,
        ToolStd,
        WorkflowDisplay,
        InvocationTime,
    },
    props: {
        markdownConfig: {
            type: Object,
            default: null,
        },
        readOnly: {
            type: Boolean,
            default: true,
        },
        exportLink: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            markdownObjects: [],
            markdownRendered: "",
            historyDatasets: {},
            historyDatasetCollections: {},
            workflows: {},
            jobs: {},
            invocations: {},
            loading: true,
        };
    },
    computed: {
        getVersion() {
            return this.markdownConfig.generate_version || "Unknown Galaxy Version";
        },
        getTime() {
            const generateTime = this.markdownConfig.generate_time;
            if (generateTime) {
                return `${generateTime.substr(0, 10)} at ${generateTime.substr(11, 5)}`;
            }
            return "unavailable";
        },
        effectiveExportLink() {
            const Galaxy = getGalaxyInstance();
            return Galaxy.config.enable_beta_markdown_export ? this.exportLink : null;
        },
    },
    created() {
        const self = this;
        md.renderer.rules.fence = function (tokens, idx, options, env, slf) {
            const token = tokens[idx];
            const info = token.info ? token.info.trim() : "";
            const content = token.content;
            if (info == "galaxy") {
                const galaxy_function = FUNCTION_CALL_LINE_TEMPLATE.exec(content);
                const args = {};
                const function_name = galaxy_function[1];
                // we need [... ] to return empty string, if regex doesn't match
                const function_arguments = [...content.matchAll(new RegExp(FUNCTION_CALL, "g"))];

                for (let i = 0; i < function_arguments.length; i++) {
                    if (function_arguments[i] === undefined) continue;
                    const arguments_str = function_arguments[i].toString().replace(/,/g, "").trim();

                    if (arguments_str) {
                        const [key, val] = arguments_str.split("=");
                        args[key.trim()] = val.replace(/['"]+/g, "").trim();
                    }
                }
                self.markdownObjects.push({
                    key: self.markdownObjects.length,
                    name: function_name,
                    args: args,
                    content: content,
                });
                return "";
            } else {
                return default_fence(tokens, idx, options, env, slf);
            }
        };
    },
    watch: {
        markdownConfig: function (mConfig, oldVal) {
            const markdown = mConfig.markdown;
            this.markdownRendered = md.render(markdown);
            this.historyDatasets = mConfig.history_datasets || {};
            this.historyDatasetCollections = mConfig.history_dataset_collections || {};
            this.workflows = mConfig.workflows || {};
            this.jobs = mConfig.jobs || {};
            this.invocations = mConfig.invocations || {};
            this.loading = false;
        },
    },
};
</script>
<style scoped>
.markdown-export {
    bottom: 0;
    right: 0;
    opacity: 0.5;
}
</style>
