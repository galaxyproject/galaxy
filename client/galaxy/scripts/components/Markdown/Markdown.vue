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
import MarkdownItContainer from "markdown-it-container";

import JOB_STATES_MODEL from "mvc/history/job-states-model";
import HDCAModel from "mvc/history/hdca-model";
import HDCAListItemEdit from "mvc/history/hdca-li-edit";

const md = MarkdownIt();

md.use(MarkdownItContainer, "history_dataset_display", {
    validate: function(params) {
        return params.trim().match(/^history_dataset_display history_dataset_id=([\w]*)$/);
    },

    render: function(tokens, idx) {
        var m = tokens[idx].info.trim().match(/^history_dataset_display history_dataset_id=([\w]*)$/);

        if (tokens[idx].nesting === 1) {
            // opening tag
            const history_dataset_id = m[1];
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
                </div>`;
        } else {
            // closing tag
            return "</div>\n";
        }
    }
});

md.use(MarkdownItContainer, "history_dataset_collection_display", {
    validate: function(params) {
        return params.trim().match(/^history_dataset_collection_display history_dataset_collection_id=([\w]*)$/);
    },

    render: function(tokens, idx) {
        var m = tokens[idx].info
            .trim()
            .match(/^history_dataset_collection_display history_dataset_collection_id=([\w]*)$/);

        if (tokens[idx].nesting === 1) {
            // opening tag
            const history_dataset_collection_id = m[1];
            return `<div class='dataset-collection' history_dataset_collection_id="${history_dataset_collection_id}">`;
        } else {
            // closing tag
            return "</div>\n";
        }
    }
});

md.use(MarkdownItContainer, "workflow_display", {
    validate: function(params) {
        return params.trim().match(/^workflow_display workflow_id=([\w]*)$/);
    },

    render: function(tokens, idx) {
        var m = tokens[idx].info.trim().match(/^workflow_display workflow_id=([\w]*)$/);

        if (tokens[idx].nesting === 1) {
            // opening tag
            const workflow_id = m[1];
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
                </div>`;
        } else {
            // closing tag
            return "</div>\n";
        }
    }
});

md.use(MarkdownItContainer, "history_dataset_as_image", {
    validate: function(params) {
        return params.trim().match(/^history_dataset_as_image history_dataset_id=([\w]*)$/);
    },

    render: function(tokens, idx) {
        var m = tokens[idx].info.trim().match(/^history_dataset_as_image history_dataset_id=([\w]*)$/);

        if (tokens[idx].nesting === 1) {
            // opening tag
            const history_dataset_id = m[1];
            return `<img src="${getAppRoot()}dataset/display?dataset_id=${history_dataset_id}">`;
        } else {
            // closing tag
            return "<br>\n";
        }
    }
});

const render_fenced_div = function(tokens, idx) {
    if (tokens[idx].nesting === 1) {
        // opening tag
        return `<div>`;
    } else {
        // closing tag
        return `</div><br>\n`;
    }
};

md.use(MarkdownItContainer, "history_dataset_peek", {
    validate: function(params) {
        return params.trim().match(/^history_dataset_peek history_dataset_id=([\w]*)$/);
    },

    render: render_fenced_div
});

md.use(MarkdownItContainer, "history_dataset_info", {
    validate: function(params) {
        return params.trim().match(/^history_dataset_info history_dataset_id=([\w]*)$/);
    },

    render: render_fenced_div
});

md.use(MarkdownItContainer, "tool_stdout", {
    validate: function(params) {
        return params.trim().match(/^tool_stdout job_id=([\w]*)$/);
    },

    render: render_fenced_div
});

md.use(MarkdownItContainer, "tool_stderr", {
    validate: function(params) {
        return params.trim().match(/^tool_stderr job_id=([\w]*)$/);
    },

    render: render_fenced_div
});

md.use(MarkdownItContainer, "job_metrics", {
    validate: function(params) {
        return params.trim().match(/^job_metrics job_id=([\w]*)$/);
    },

    render: function(tokens, idx) {
        var m = tokens[idx].info.trim().match(/^job_metrics job_id=([\w]*)$/);

        if (tokens[idx].nesting === 1) {
            // opening tag
            const jobId = m[1];
            return `<div class="job-metrics" job_id="${jobId}">`;
        } else {
            // closing tag
            return "</div>\n";
        }
    }
});

md.use(MarkdownItContainer, "job_parameters", {
    validate: function(params) {
        return params.trim().match(/^job_parameters job_id=([\w]*)$/);
    },

    render: function(tokens, idx) {
        var m = tokens[idx].info.trim().match(/^job_parameters job_id=([\w]*)$/);

        if (tokens[idx].nesting === 1) {
            // opening tag
            const jobId = m[1];
            return `<div class="job-parameters" job_id="${jobId}">`;
        } else {
            // closing tag
            return "</div>\n";
        }
    }
});

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
            workflows: {}
        };
    },
    watch: {
        markdownConfig: function(mConfig, oldVal) {
            const markdown = mConfig.markdown;
            this.markdownRendered = md.render(markdown);
            this.historyDatasets = mConfig.history_datasets || {};
            this.historyDatasetCollections = mConfig.history_dataset_collections || {};
            this.workflows = mConfig.workflows || {};

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
