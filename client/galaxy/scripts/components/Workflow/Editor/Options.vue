<template>
    <div class="panel-header-buttons">
        <a
            id="workflow-run-button"
            class="panel-header-button"
            href="javascript:void(0)"
            role="button"
            title="Run"
            aria-label="Run"
            @click="navigateToRun"
            v-show="mode == 'canvas'"
        >
            <span class="fa fa-play"></span>
        </a>
        <a
            id="workflow-save-button"
            class="panel-header-button"
            href="javascript:void(0)"
            role="button"
            title="Save"
            aria-label="Save"
            @click="save"
            v-show="mode == 'canvas'"
        >
            <span class="fa fa-floppy-o"></span>
        </a>
        <a
            id="workflow-report-button"
            class="panel-header-button"
            href="javascript:void(0)"
            role="button"
            title="Edit Report"
            aria-label="Edit Report"
            v-show="mode == 'canvas'"
            @click="setMode('report')"
        >
            <span class="fa fa-edit"></span>
        </a>
        <a
            id="workflow-report-help-button"
            class="panel-header-button"
            href="javascript:void(0)"
            role="button"
            title="Report Syntax Help"
            aria-label="Report Syntax Help"
            @click="showReportHelp"
            v-show="mode == 'report'"
        >
            <span class="fa fa-question"></span>
        </a>
        <a
            id="workflow-canvas-button"
            class="panel-header-button"
            href="javascript:void(0)"
            role="button"
            title="Edit Workflow"
            aria-label="Edit Workflow"
            @click="setMode('canvas')"
            v-show="mode == 'report'"
        >
            <span class="fa fa-sitemap fa-rotate-270"></span>
        </a>
        <a
            id="workflow-options-button"
            class="panel-header-button"
            href="javascript:void(0)"
            role="button"
            title="Workflow options"
            aria-label="Workflow options"
            ref="save-button"
            v-show="mode == 'canvas'"
        >
            <span class="fa fa-cog"/>
        </a>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";

export default {
    props: {
        editorConfig: {
            type: Object
        }
    },
    data() {
        return {
            mode: "canvas"
        };
    },
    mounted() {
        /*this.workflowView = new WorkflowView(this.editorConfig, this.$refs["report-editor"]);
        make_popupmenu($(this.$refs["save-button"]), {
            "Save As": () => this.workflowView.workflow_save_as(),
            "Edit Attributes": () => {
                this.workflowView.workflow.clear_active_node();
            },
            "Auto Re-layout": () => this.workflowView.layout_editor(),
            Download: {
                url: `${getAppRoot()}api/workflows/${this.editorConfig.id}/download?format=json-download`,
                action: function() {}
            }
        });*/
    },
    methods: {
        setMode(mode) {
            this.mode = mode;
        },
        onReportUpdate(markdown) {
            this.workflowView.report_changed(markdown);
        },
        navigateToRun() {
            window.location = `${getAppRoot()}workflows/run?id=${this.editorConfig.id}`;
        },
        save() {
            this.workflowView.save_current_workflow();
        }
    }
};
</script>