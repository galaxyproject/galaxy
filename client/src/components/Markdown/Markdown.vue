<template>
    <div class="markdown-wrapper">
        <LoadingSpan v-if="loading" />
        <div v-else>
            <div>
                <StsDownloadButton
                    v-if="effectiveExportLink"
                    class="float-right markdown-pdf-export"
                    :fallback-url="exportLink"
                    :download-endpoint="downloadEndpoint"
                    size="sm"
                    title="Generate PDF">
                </StsDownloadButton>
                <b-button
                    v-if="!readOnly"
                    v-b-tooltip.hover
                    class="float-right markdown-edit mr-2"
                    role="button"
                    size="sm"
                    title="Edit Markdown"
                    @click="$emit('onEdit')">
                    Edit
                    <FontAwesomeIcon icon="edit" />
                </b-button>
                <h1 class="float-right align-middle mr-2 mt-1 h-md">Galaxy {{ markdownConfig.model_class }}</h1>
                <span class="float-left font-weight-light">
                    <h1 class="text-break align-middle">
                        Title: {{ markdownConfig.title || markdownConfig.model_class }}
                    </h1>
                    <h2 v-if="workflowVersions" class="text-break align-middle">
                        Workflow Checkpoint: {{ workflowVersions.version }}
                    </h2>
                </span>
            </div>
            <b-badge variant="info" class="w-100 rounded mb-3 white-space-normal">
                <div class="float-left m-1 text-break">Generated with Galaxy {{ version }} on {{ time }}</div>
                <div class="float-right m-1">Identifier: {{ markdownConfig.id }}</div>
            </b-badge>
            <div>
                <b-alert v-if="markdownErrors.length > 0" variant="warning" show>
                    <div v-for="(obj, index) in markdownErrors" :key="index" class="mb-1">
                        <h2 class="h-text">{{ obj.error || "Error" }}</h2>
                        {{ obj.line }}
                    </div>
                </b-alert>
            </div>
            <div v-for="(obj, index) in markdownObjects" :key="index" class="markdown-components">
                <p v-if="obj.name == 'default'" class="text-justify m-2" v-html="obj.content" />
                <MarkdownContainer
                    v-else
                    :name="obj.name"
                    :args="obj.args"
                    :datasets="datasets"
                    :collections="collections"
                    :histories="histories"
                    :invocations="invocations"
                    :time="time"
                    :version="version"
                    :workflows="workflows" />
            </div>
        </div>
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faDownload, faEdit } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BootstrapVue from "bootstrap-vue";
import MarkdownIt from "markdown-it";
import markdownItRegexp from "markdown-it-regexp";
import { mapActions } from "pinia";
import Vue from "vue";

import { useWorkflowStore } from "@/stores/workflowStore";

import MarkdownContainer from "./MarkdownContainer.vue";
import LoadingSpan from "components/LoadingSpan.vue";
import StsDownloadButton from "components/StsDownloadButton.vue";

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
    components: {
        MarkdownContainer,
        FontAwesomeIcon,
        LoadingSpan,
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
            datasets: {},
            histories: {},
            collections: {},
            workflows: {},
            invocations: {},
            loading: true,
            workflowID: "",
        };
    },
    computed: {
        effectiveExportLink() {
            return this.enable_beta_markdown_export ? this.exportLink : null;
        },
        time() {
            let generateTime = this.markdownConfig.generate_time;
            if (generateTime) {
                if (!generateTime.endsWith("Z")) {
                    // We don't have tzinfo, but this will always be UTC coming
                    // from Galaxy so append Z to assert that prior to parsing
                    generateTime += "Z";
                }
                const date = new Date(generateTime);
                return date.toLocaleString("default", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                    minute: "numeric",
                    hour: "numeric",
                    timeZone: "UTC",
                    timeZoneName: "short",
                });
            }
            return "unavailable";
        },
        workflowVersions() {
            return this.getStoredWorkflowByInstanceId(this.workflowID);
        },
        version() {
            return this.markdownConfig.generate_version || "Unknown Galaxy Version";
        },
    },
    watch: {
        markdownConfig() {
            this.initConfig();
        },
    },
    created() {
        this.initConfig();
        this.fetchWorkflowForInstanceId(this.workflowID);
    },
    methods: {
        ...mapActions(useWorkflowStore, ["getStoredWorkflowByInstanceId", "fetchWorkflowForInstanceId"]),
        initConfig() {
            if (Object.keys(this.markdownConfig).length) {
                const config = this.markdownConfig;
                const markdown = config.content || config.markdown || "";
                this.markdownErrors = config.errors || [];
                this.markdownObjects = this.splitMarkdown(markdown);
                this.datasets = config.history_datasets || {};
                this.histories = config.histories || {};
                this.collections = config.history_dataset_collections || {};
                this.workflows = config.workflows || {};
                this.invocations = config.invocations || {};
                this.loading = false;
                this.workflowID = Object.keys(this.markdownConfig.workflows)[0];
            }
        },
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
    },
};
</script>
