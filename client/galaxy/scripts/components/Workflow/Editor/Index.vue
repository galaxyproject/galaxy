<template>
    <div id="center" class="inbound">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <span class="sr-only">Workflow Editor</span>
                {{ editorConfig.name }}
                <WorkflowOptions
                    :canvas="isCanvas"
                    @onSave="onSave"
                    @onSaveAs="onSaveAs"
                    @onRun="onRun"
                    @onDownload="onDownload"
                    @onReport="onReport"
                    @onReportHelp="onReportHelp"
                    @onLayout="onLayout"
                    @onEdit="onEdit"
                    @onAttributes="onAttributes"
                />
            </div>
        </div>
        <div class="unified-panel-body" id="workflow-canvas-body" v-show="isCanvas">
            <div id="canvas-viewport" class="workflow-canvas-content">
                <div id="canvas-container" />
            </div>
            <div id="workflow-parameters-box">
                <span class="workflow-parameters-box-title">
                    Workflow Parameters
                </span>
                <div id="workflow-parameters-container" />
            </div>
            <div class="workflow-overview" aria-hidden="true">
                <div class="workflow-overview-body">
                    <div id="overview">
                        <canvas width="0" height="0" id="overview-canvas" />
                        <div id="overview-viewport" />
                    </div>
                </div>
            </div>
        </div>
        <div class="unified-panel-body workflow-report-body" v-show="!isCanvas">
            <markdown-editor ref="report-editor" initial-markdown="" :onupdate="onReportUpdate" :toolbar="false" />
        </div>
    </div>
</template>

<script>
import { WorkflowView } from "mvc/workflow/workflow-view";
import WorkflowOptions from "./Options";
import MarkdownEditor from "components/Markdown/MarkdownEditor";
import { getAppRoot } from "onload/loadConfig";
import { showReportHelp } from "./reportHelp";

export default {
    components: { MarkdownEditor, WorkflowOptions },
    props: {
        editorConfig: {
            type: Object
        }
    },
    data() {
        return {
            isCanvas: true
        };
    },
    mounted() {
        this.workflowView = new WorkflowView(this.editorConfig, this.$refs["report-editor"]);
    },
    methods: {
        onDownload() {
            window.location = `${getAppRoot()}api/workflows/${this.editorConfig.id}/download?format=json-download`;
        },
        onSaveAs() {
            this.workflowView.workflow_save_as();
        },
        onLayout() {
            this.workflowView.layout_editor();
        },
        onAttributes() {
            this.workflowView.workflow.clear_active_node();
        },
        onEdit() {
            this.isCanvas = true;
        },
        onReport() {
            this.isCanvas = false;
        },
        onReportUpdate(markdown) {
            this.workflowView.report_changed(markdown);
        },
        onRun() {
            window.location = `${getAppRoot()}workflows/run?id=${this.editorConfig.id}`;
        },
        onSave() {
            this.workflowView.save_current_workflow();
        },
        onReportHelp() {
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
