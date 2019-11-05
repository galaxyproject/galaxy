<template>
    <div id="center" class="inbound">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <span class="sr-only">Workflow Editor&nbsp;</span>
                {{ editorConfig["name"] }}
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
                        <span class="fa fa-cog"></span>
                    </a>
                </div>
            </div>
        </div>
        <div class="unified-panel-body" id="workflow-canvas-body" v-show="mode == 'canvas'">
            <div id="canvas-viewport" class="workflow-canvas-content">
                <div id="canvas-container"></div>
            </div>
            <div id="workflow-parameters-box">
                <span class="workflow-parameters-box-title">
                    Workflow Parameters
                </span>
                <div id="workflow-parameters-container"></div>
            </div>
            <div class="workflow-overview" v-show="mode == 'canvas'" aria-hidden="true">
                <div class="workflow-overview-body">
                    <div id="overview">
                        <canvas width="0" height="0" id="overview-canvas"></canvas>
                        <div id="overview-viewport"></div>
                    </div>
                </div>
            </div>
        </div>
        <div class="unified-panel-body workflow-report-body" v-show="mode == 'report'">
            <markdown-editor ref="report-editor" initial-markdown="" :onupdate="onReportUpdate" />
        </div>
    </div>
</template>

<script>
import $ from "jquery";
import WorkflowView from "mvc/workflow/workflow-view";
import MarkdownEditor from "components/Markdown/MarkdownEditor";
import { getAppRoot } from "onload/loadConfig";
import { showReportHelp } from "./reportHelp";
import { make_popupmenu } from "ui/popupmenu";

export default {
    components: { MarkdownEditor },
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
        this.workflowView = new WorkflowView(this.editorConfig, this.$refs["report-editor"]);
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
        });
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
        },
        showReportHelp() {
            showReportHelp();
        }
    }
};
</script>

<style scoped>
#center {
    z-index: 0;
    display: flex;
    flex-direction: column;
    flex-grow: 1;
}

.workflow-report-body {
    display: flex;
}

.workflow-overview-body {
    position: relative;
    overflow: hidden;
    width: 100%;
    height: 100%;
    border-top: solid gray 1px;
    border-left: solid grey 1px;
}

#canvas-container {
    position: absolute;
    width: 100%;
    height: 100%;
}

#workflow-parameters-box {
    display: none;
    position: absolute;
    right: 0px;
    border: solid grey 1px;
    padding: 5px;
    background: #eeeeee;
    z-index: 20000;
    overflow: auto;
    max-width: 300px;
    max-height: 300px;
}

.workflow-parameters-box-title {
    display: block;
    margin-bottom: 5px;
    font-weight: bold;
}

#overview {
    position: absolute;
}

#overview-canvas {
    background: white;
    width: 100%;
    height: 100%;
}

#overview-viewport {
    position: absolute;
    width: 0px;
    height: 0px;
    border: solid blue 1px;
    z-index: 10;
}
</style>

<style>
canvas {
    position: absolute;
    z-index: 10;
}
canvas.dragging {
    position: absolute;
    z-index: 1000;
}
</style>
