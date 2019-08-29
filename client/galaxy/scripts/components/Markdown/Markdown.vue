<template>
    <div class="markdown-wrapper">
        <div v-html="markdownRendered"></div>
    </div>
</template>

<script>
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import { render_embedded_items } from "mvc/embedded-objects";
import { mountJobMetrics } from "components/JobMetrics";
import { mountJobParameters } from "components/JobParameters";
import MarkdownIt from "markdown-it";

import JOB_STATES_MODEL from "mvc/history/job-states-model";
import HDCAModel from "mvc/history/hdca-model";
import HDCAListItemEdit from "mvc/history/hdca-li-edit";

const FUNCTION_CALL_LINE_TEMPLATE = /\s*(\w+)\s*\((\s*\w+\s*=\s*\w+\s*)\)\s*/m;

const md = MarkdownIt();

const default_fence = md.renderer.rules.fence;

const RENDER_FUNCTIONS = {
    history_dataset_display: (action, args, content) => {
        const history_dataset_id = args.history_dataset_id;
        return `<div class='embedded-item display dataset'>
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
                <input type="hidden" name="ajax-item-content-url" value="${getAppRoot()}dataset/get_item_content_async?id=${history_dataset_id}">
            </div>
            <div class='summary-content'>
            </div>
            <div class='expanded-content'>
                <div class='item-content'>
                </div>
            </div>
        </div>`;
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
        return `<img src="${getAppRoot()}dataset/display?dataset_id=${history_dataset_id}"></img>`;
    },
    history_dataset_peek: (action, args, content) => {
        const history_dataset_id = args.history_dataset_id;
        return `<div class='dataset-peek' history_dataset_id="${history_dataset_id}"><pre><code></code></pre></div>`;
    },
    history_dataset_info: (action, args, content) => {
        const history_dataset_id = args.history_dataset_id;
        return `<div class='dataset-info' history_dataset_id="${history_dataset_id}"><pre><code></code></pre></div>`;
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
        return `<div class="job-parameters" job_id="${jobId}"></div>`;
    }
};

md.renderer.rules.fence = function(tokens, idx, options, env, slf) {
    const token = tokens[idx],
        info = token.info ? token.info.trim() : "",
        content = token.content;
    if (info == "galaxy") {
        const arr = FUNCTION_CALL_LINE_TEMPLATE.exec(content);
        const action = arr[1];
        const arguments_str = arr[2].trim();
        const args = {};
        if (arguments_str) {
            const parts = arguments_str.split(/(\s+)/);
            for (const part of parts) {
                const [key, val] = part.split("=");
                args[key.trim()] = val.trim();
            }
        }
        return RENDER_FUNCTIONS[action](action, args, content);
    } else {
        return default_fence(tokens, idx, options, env, slf);
    }
};

function render_fenced_output(tag, objects, idAttr, metadataKey) {
    $("." + tag).each((i, el) => {
        const objectId = $(el).attr(idAttr);
        const meta = objects[objectId][metadataKey];
        $(el)
            .find("code")
            .text(meta);
    });
}

export default {
    props: {
        markdownConfig: {
            type: Object
        }
    },
    data() {
        return {
            markdownRendered: "",
            historyDatasets: {},
            historyDatasetCollections: {},
            workflows: {},
            jobs: {}
        };
    },
    watch: {
        markdownConfig: function(mConfig, oldVal) {
            const markdown = mConfig.markdown;
            this.markdownRendered = md.render(markdown);
            this.historyDatasets = mConfig.history_datasets || {};
            this.historyDatasetCollections = mConfig.history_dataset_collections || {};
            this.workflows = mConfig.workflows || {};
            this.jobs = mConfig.jobs || {};

            this.$nextTick(() => {
                render_embedded_items();
                mountJobMetrics({ includeTitle: false });
                mountJobParameters({ includeTitle: false });
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

                $(".dataset-collection").each((i, el) => {
                    const Galaxy = getGalaxyInstance();
                    const hdcaId = $(el).attr("history_dataset_collection_id");
                    const hdca = this.historyDatasetCollections[hdcaId];
                    const hdcaModel = new HDCAModel.HistoryDatasetCollection(hdca);

                    const jobStateSummariesCollection = new JOB_STATES_MODEL.JobStatesSummaryCollection();
                    jobStateSummariesCollection.historyId = hdca["history_id"];
                    jobStateSummariesCollection.monitor();
                    jobStateSummariesCollection.trackModel(hdcaModel);

                    return new HDCAListItemEdit.HDCAListItemEdit({
                        model: hdcaModel,
                        el: $(el),
                        linkTarget: "galaxy_main",
                        purgeAllowed: Galaxy.config.allow_user_dataset_purge,
                        logger: Galaxy.logger
                    }).render(0);
                });
            });
        }
    }
};
</script>

<style lang="scss">
// Load styling developed for "pages" embedded content.
@import "embed_item";
.toggle {
    display: none;
}
</style>
