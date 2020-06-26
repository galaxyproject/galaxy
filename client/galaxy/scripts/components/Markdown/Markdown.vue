<template>
    <div class="markdown-wrapper">
        <div v-html="markdownRendered"></div>
        <a :href="exportLink" class="markdown-export" v-if="effectiveExportLink">
            <i class="fa fa-4x fa-download"></i>
        </a>
    </div>
</template>

<script>
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import { render_embedded_items } from "mvc/embedded-objects";
import { mountJobMetrics } from "components/JobMetrics";
import { mountJobParameters } from "components/JobParameters";
import { mountDatasetComponents } from "components/Dataset/mount";
import MarkdownIt from "markdown-it";

import JOB_STATES_MODEL from "mvc/history/job-states-model";
import HDCAModel from "mvc/history/hdca-model";
import HDCAListItemEdit from "mvc/history/hdca-li-edit";
import HDCAListItem from "mvc/history/hdca-li";
const FUNCTION_VALUE_REGEX = `\\s*(?:[\\w_\\-]+|\\"[^\\"]+\\"|\\'[^\\']+\\')\\s*`;
const FUNCTION_CALL = `\\s*\\w+\\s*=` + FUNCTION_VALUE_REGEX;
const FUNCTION_CALL_LINE = `\\s*(\\w+)\\s*\\(\\s*(?:(${FUNCTION_CALL})(,${FUNCTION_CALL})*)?\\s*\\)\\s*`;
const FUNCTION_CALL_LINE_TEMPLATE = new RegExp(FUNCTION_CALL_LINE, "m");

const md = MarkdownIt();

const default_fence = md.renderer.rules.fence;

const RENDER_FUNCTIONS = {
    history_dataset_display: (action, args, content) => {
        const history_dataset_id = args.history_dataset_id;
        return `<div class='embedded-item display dataset' data-item-url="${getAppRoot()}dataset/get_item_content_async?id=${history_dataset_id}">
            <div class='title'>
                <div style="float: left">
                <a class="display_in_embed icon-button toggle-expand" title="Show Dataset content"></a>
                <a class="toggle icon-button" title="Hide Dataset content"></a>
                </div>
                <div style="float: right">
                <a href="${getAppRoot()}dataset/display?dataset_id=${history_dataset_id}" class="icon-button disk" title="Save dataset"></a>
                <a href="${getAppRoot()}dataset/imp?dataset_id=${history_dataset_id}" class="icon-button import" title="Import dataset"></a>
                </div>
                <a class="toggle-embed"><h4>Galaxy Dataset | <span class="render-name" history_dataset_id="${history_dataset_id}"></span</h4></a>
            </div>
            <div class='summary-content'>
            </div>
            <div class='expanded-content'>
                <div class='item-content'>
                </div>
            </div>
        </div>`;
    },
    history_dataset_embedded: (action, args, content) => {
        const history_dataset_id = args.history_dataset_id;
        return `<div class='embedded-item display expanded' data-item-url="${getAppRoot()}dataset/get_item_content_async?id=${history_dataset_id}">
            <div class='expanded-content'>
                <div class='item-content'>
                </div>
            </div>
        </div>`;
    },
    history_dataset_link: (action, args, content) => {
        const history_dataset_id = args.history_dataset_id;
        const path = args.path;
        const label = args.label;
        return `<div class="dataset-link" history_dataset_id="${history_dataset_id}" path="${path}" label="${label}"></div>`;
    },
    history_dataset_index: (action, args, content) => {
        const history_dataset_id = args.history_dataset_id;
        const path = args.path;
        return `<div class="dataset-index" history_dataset_id="${history_dataset_id}" path="${path}"></div>`;
    },
    history_dataset_collection_display: (action, args, content) => {
        const history_dataset_collection_id = args.history_dataset_collection_id;
        return `<div class='dataset-collection' history_dataset_collection_id="${history_dataset_collection_id}"></div>`;
    },
    workflow_display: (action, args, content) => {
        const workflow_id = args.workflow_id;
        return `<div class='embedded-item display workflow'>
            <div class='title'>
                <div style="float: left">
                <a class="display_in_embed icon-button toggle-expand" title="Show Workflow content"></a>
                <a class="toggle icon-button" title="Hide Workflow content"></a>
                </div>
                <div style="float: right">
                <!-- fix URL -->
                <a href="${getAppRoot()}api/workflows/${workflow_id}/download?format=json-download" class="icon-button disk" title="Save workflow"></a>
                </div>
                <a class="toggle-embed"><h4>Galaxy Workflow | <span class="render-name" workflow_id="${workflow_id}"></span></h4></a>
                <input type="hidden" name="ajax-item-content-url" value="${getAppRoot()}workflow/get_item_content_async?id=${workflow_id}">
            </div>
            <div class='summary-content'>
            </div>
            <div class='expanded-content'>
                <div class='item-content'>
                </div>
            </div>
        </div>`;
    },
    history_dataset_as_image: (action, args, content) => {
        const history_dataset_id = args.history_dataset_id;
        const path = args.path;
        if (path) {
            `${getAppRoot}api/histories/${history_dataset_id}/contents/${history_dataset_id}/display?filename=${path}`;
        }
        return `<div class="dataset-as-image" history_dataset_id="${history_dataset_id}" path="${path}"></div>`;
    },
    history_dataset_peek: (action, args, content) => {
        const history_dataset_id = args.history_dataset_id;
        return `<div class='dataset-peek' history_dataset_id="${history_dataset_id}"><pre><code></code></pre></div>`;
    },
    history_dataset_info: (action, args, content) => {
        const history_dataset_id = args.history_dataset_id;
        return `<div class='dataset-info' history_dataset_id="${history_dataset_id}"><pre><code></code></pre></div>`;
    },
    history_dataset_name: (action, args, contents) => {
        const history_dataset_id = args.history_dataset_id;
        return `<div class='dataset-name' history_dataset_id="${history_dataset_id}"><pre><code></code></pre></div>`;
    },
    history_dataset_type: (actions, args, contents) => {
        const history_dataset_id = args.history_dataset_id;
        return `<div class='dataset-type' history_dataset_id="${history_dataset_id}"><pre><code></code></pre></div>`;
    },
    tool_stdout: (action, args, content) => {
        const jobId = args.job_id;
        return `<div class="tool-stdout" job_id="${jobId}"><pre><code></code></pre></div>`;
    },
    tool_stderr: (action, args, content) => {
        const jobId = args.job_id;
        return `<div class="tool-stderr" job_id="${jobId}"><pre><code></code></pre></div>`;
    },
    job_metrics: (action, args, content) => {
        const jobId = args.job_id;
        return `<div class="job-metrics" job_id="${jobId}"></div>`;
    },
    job_parameters: (action, args, content) => {
        const jobId = args.job_id;
        const param = args.param;
        return `<div class="job-parameters" job_id="${jobId}" param="${param}"></div>`;
    },
    generate_galaxy_version: (actions, args, content) => {
        return `<div class="galaxy-version"><pre><code></code></pre></div>`;
    },
    generate_time: (actions, args, content) => {
        return `<div class="generate-time"><pre><code></code></pre></div>`;
    },
    invocation_time: (actions, args, content) => {
        const invocationId = args.invocation_id;
        return `<div class="invocation-time" invocation_id="${invocationId}"><pre><code></code></pre></div>`;
    },
};

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

        return RENDER_FUNCTIONS[function_name](function_name, args, content);
    } else {
        return default_fence(tokens, idx, options, env, slf);
    }
};

function render_fenced_output(tag, objects, idAttr, metadataKey) {
    $("." + tag).each((i, el) => {
        const objectId = $(el).attr(idAttr);
        const meta = objects[objectId][metadataKey];
        $(el).find("code").text(meta);
    });
}

export default {
    props: {
        markdownConfig: {
            type: Object,
        },
        readOnly: {
            type: Boolean,
            default: true,
        },
        exportLink: {
            type: String,
            required: false,
        },
    },
    data() {
        return {
            markdownRendered: "",
            historyDatasets: {},
            historyDatasetCollections: {},
            workflows: {},
            jobs: {},
            invocations: {},
            generateTime: null,
            generateGalaxyVersion: null,
        };
    },
    computed: {
        effectiveExportLink() {
            const Galaxy = getGalaxyInstance();
            return Galaxy.config.enable_beta_markdown_export ? this.exportLink : null;
        },
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
            this.generateGalaxyVersion = mConfig.generate_version || "Unknown Galaxy Version";
            this.generateTime = mConfig.generate_time;

            this.$nextTick(() => {
                render_embedded_items();
                mountJobMetrics({ includeTitle: false });
                mountJobParameters({ includeTitle: false });
                mountDatasetComponents();

                $("span.render-name").each((i, el) => {
                    const historyDatasetId = $(el).attr("history_dataset_id");
                    if (historyDatasetId) {
                        $(el).text(this.historyDatasets[historyDatasetId]["name"]);
                    }
                    const workflowId = $(el).attr("workflow_id");
                    if (workflowId) {
                        $(el).text(this.workflows[workflowId]["name"]);
                    }
                });

                render_fenced_output("tool-stdout", this.jobs, "job_id", "tool_stdout");
                render_fenced_output("tool-stderr", this.jobs, "job_id", "tool_stderr");
                render_fenced_output("dataset-peek", this.historyDatasets, "history_dataset_id", "peek");
                render_fenced_output("dataset-info", this.historyDatasets, "history_dataset_id", "info");
                render_fenced_output("dataset-name", this.historyDatasets, "history_dataset_id", "name");
                render_fenced_output("dataset-type", this.historyDatasets, "history_dataset_id", "ext");

                $(".galaxy-version code").text(this.generateGalaxyVersion);
                $(".generate-time code").text(this.generateTime);

                render_fenced_output("invocation-time", this.invocations, "invocation_id", "create_time");

                $(".dataset-collection").each((i, el) => {
                    const Galaxy = getGalaxyInstance();
                    const hdcaId = $(el).attr("history_dataset_collection_id");
                    const hdca = this.historyDatasetCollections[hdcaId];
                    const hdcaModel = new HDCAModel.HistoryDatasetCollection(hdca);

                    const jobStateSummariesCollection = new JOB_STATES_MODEL.JobStatesSummaryCollection();
                    jobStateSummariesCollection.historyId = hdca["history_id"];
                    jobStateSummariesCollection.monitor();
                    jobStateSummariesCollection.trackModel(hdcaModel);
                    const viewClass = this.readOnly ? HDCAListItem.HDCAListItemView : HDCAListItemEdit.HDCAListItemEdit;
                    return new viewClass({
                        model: hdcaModel,
                        el: $(el),
                        linkTarget: "galaxy_main",
                        purgeAllowed: Galaxy.config.allow_user_dataset_purge,
                        logger: Galaxy.logger,
                    }).render(0);
                });
            });
        },
    },
};
</script>

<style lang="scss">
// Load styling developed for "pages" embedded content.
@import "embed_item";
.toggle {
    display: none;
}

.markdown-export {
    position: absolute;
    bottom: 0;
    right: 0;
    z-index: 2000;
    padding: 1rem;
    color: gray;
    opacity: 0.5;
}
</style>
