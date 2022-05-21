<template>
    <div class="markdown-wrapper">
        <LoadingSpan v-if="loading" />
        <div v-else>
            <div>
                <sts-download-button
                    v-if="effectiveExportLink"
                    class="float-right markdown-pdf-export"
                    :fallback-url="exportLink"
                    :download-endpoint="downloadEndpoint"
                    title="Download PDF"></sts-download-button>
                <b-button
                    v-if="!readOnly"
                    v-b-tooltip.hover.bottom
                    class="float-right markdown-edit"
                    title="Edit Markdown"
                    variant="link"
                    role="button"
                    @click="$emit('onEdit')">
                    <font-awesome-icon icon="edit" />
                </b-button>
                <h3 class="float-right align-middle mr-1 mt-2">Galaxy {{ markdownConfig.model_class }}</h3>
                <span class="float-left font-weight-light mb-3">
                    <small>Title: {{ markdownConfig.title || markdownConfig.model_class }}</small
                    ><br />
                    <small>Username: {{ markdownConfig.username }}</small>
                </span>
            </div>
            <b-badge variant="info" class="w-100 rounded mb-3">
                <div class="float-left m-1">Created with Galaxy {{ getVersion }} on {{ getTime }}</div>
                <div class="float-right m-1">Identifier {{ markdownConfig.id }}</div>
            </b-badge>
            <div>
                <b-alert v-if="markdownErrors.length > 0" variant="warning" show>
                    <div v-for="(obj, index) in markdownErrors" :key="index" class="mb-1">
                        <h5>{{ obj.error || "Error" }}</h5>
                        {{ obj.line }}
                    </div>
                </b-alert>
            </div>
            <div v-for="(obj, index) in markdownObjects" :key="index" class="markdown-components">
                <p v-if="obj.name == 'default'" class="text-justify m-2" v-html="obj.content" />
                <div v-else-if="obj.name == 'generate_galaxy_version'" class="galaxy-version">
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
                    :collections="historyDatasetCollections" />
                <ToolStd
                    v-else-if="['tool_stdout', 'tool_stderr'].includes(obj.name)"
                    :args="obj.args"
                    :name="obj.name"
                    :jobs="jobs" />
                <HistoryDatasetDisplay
                    v-else-if="['history_dataset_embedded', 'history_dataset_display'].includes(obj.name)"
                    :args="obj.args"
                    :datasets="historyDatasets"
                    :embedded="obj.name == 'history_dataset_embedded'" />
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
                    :datasets="historyDatasets" />
            </div>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import store from "store";
import MarkdownIt from "markdown-it";
import markdownItRegexp from "markdown-it-regexp";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faDownload, faEdit } from "@fortawesome/free-solid-svg-icons";

import LoadingSpan from "components/LoadingSpan";
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
import StsDownloadButton from "./StsDownloadButton";

const FUNCTION_VALUE_REGEX = `\\s*(?:[\\w_\\-]+|\\"[^\\"]+\\"|\\'[^\\']+\\')\\s*`;
const FUNCTION_CALL = `\\s*[\\w\\|]+\\s*=` + FUNCTION_VALUE_REGEX;
const FUNCTION_CALL_LINE = `\\s*(\\w+)\\s*\\(\\s*(?:(${FUNCTION_CALL})(,${FUNCTION_CALL})*)?\\s*\\)\\s*`;
const FUNCTION_CALL_LINE_TEMPLATE = new RegExp(FUNCTION_CALL_LINE, "m");

const mdNewline = markdownItRegexp(/<br>/, () => {
    return "<div style='clear:both;'/><br>";
});

const md = MarkdownIt();
md.use(mdNewline);

Vue.use(BootstrapVue);

library.add(faDownload, faEdit);

export default {
    store: store,
    components: {
        HistoryDatasetDetails,
        HistoryDatasetAsImage,
        HistoryDatasetCollectionDisplay,
        HistoryDatasetDisplay,
        HistoryDatasetIndex,
        HistoryDatasetLink,
        HistoryLink,
        JobMetrics,
        JobParameters,
        LoadingSpan,
        ToolStd,
        WorkflowDisplay,
        Visualization,
        InvocationTime,
        FontAwesomeIcon,
        StsDownloadButton,
    },
    props: {
        markdownConfig: {
            type: Object,
            default: null,
        },
        enable_beta_markdown_export: {
            type: Boolean,
            default: false,
        },
        downloadEndpoint: {
            type: String,
            default: null,
        },
        readOnly: {
            type: Boolean,
            default: false,
        },
        exportLink: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            markdownObjects: [],
            markdownErrors: [],
            historyDatasets: {},
            histories: {},
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
                const date = new Date(generateTime);
                return date.toLocaleString("default", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                    minute: "numeric",
                    hour: "numeric",
                });
            }
            return "unavailable";
        },
        effectiveExportLink() {
            return this.enable_beta_markdown_export ? this.exportLink : null;
        },
    },
    watch: {
        markdownConfig: function (config) {
            const markdown = config.markdown;
            this.markdownErrors = config.errors || [];
            this.markdownObjects = this.splitMarkdown(markdown);
            this.historyDatasets = config.history_datasets || {};
            this.histories = config.histories || {};
            this.historyDatasetCollections = config.history_dataset_collections || {};
            this.workflows = config.workflows || {};
            this.jobs = config.jobs || {};
            this.invocations = config.invocations || {};
            this.loading = false;
        },
    },
    methods: {
        splitMarkdown(markdown) {
            const sections = [];
            let digest = markdown;
            while (digest.length > 0) {
                const galaxyStart = digest.indexOf("```galaxy");
                if (galaxyStart != -1) {
                    const galaxyEnd = digest.substr(galaxyStart + 1).indexOf("```");
                    if (galaxyEnd != -1) {
                        if (galaxyStart > 0) {
                            const defaultContent = digest.substr(0, galaxyStart).trim();
                            if (defaultContent) {
                                sections.push({
                                    name: "default",
                                    content: md.render(defaultContent),
                                });
                            }
                        }
                        const galaxyEndIndex = galaxyEnd + 4;
                        const galaxySection = digest.substr(galaxyStart, galaxyEndIndex);
                        let args = null;
                        try {
                            args = this.getArgs(galaxySection);
                            sections.push(args);
                        } catch (e) {
                            this.markdownErrors.push({
                                error: "Found an unresolved tag.",
                                line: galaxySection,
                            });
                        }
                        digest = digest.substr(galaxyStart + galaxyEndIndex);
                    } else {
                        digest = digest.substr(galaxyStart + 1);
                    }
                } else {
                    sections.push({
                        name: "default",
                        content: md.render(digest),
                    });
                    break;
                }
            }
            return sections;
        },
        getArgs(content) {
            const galaxy_function = FUNCTION_CALL_LINE_TEMPLATE.exec(content);
            const args = {};
            const function_name = galaxy_function[1];
            // we need [... ] to return empty string, if regex doesn't match
            const function_arguments = [...content.matchAll(new RegExp(FUNCTION_CALL, "g"))];
            for (let i = 0; i < function_arguments.length; i++) {
                if (function_arguments[i] === undefined) {
                    continue;
                }
                const arguments_str = function_arguments[i].toString().replace(/,/g, "").trim();
                if (arguments_str) {
                    const [key, val] = arguments_str.split("=");
                    args[key.trim()] = val.replace(/['"]+/g, "").trim();
                }
            }
            return {
                name: function_name,
                args: args,
                content: content,
            };
        },
        onDownload() {
            window.location.href = this.exportLink;
        },
    },
};
</script>
