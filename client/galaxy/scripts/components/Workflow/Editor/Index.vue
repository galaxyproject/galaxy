<template>
    <div id="columns">
        <SidePanel id="left" side="left">
            <template v-slot:panel>
                <ToolBoxWorkflow
                    :toolbox="toolbox"
                    :module-sections="module_sections"
                    :data-managers="data_managers"
                    :workflows="workflows"
                    @onInsertTool="onInsertTool"
                    @onInsertModule="onInsertModule"
                    @onInsertWorkflow="onInsertWorkflow"
                    @onInsertWorkflowSteps="onInsertWorkflowSteps"
                />
            </template>
        </SidePanel>
        <div id="center" class="inbound">
            <div class="unified-panel-header" unselectable="on">
                <div class="unified-panel-header-inner">
                    <span class="sr-only">Workflow Editor</span>
                    {{ name }}
                </div>
            </div>
            <div class="unified-panel-body" id="workflow-canvas-body" v-show="isCanvas">
                <div id="canvas-viewport" class="workflow-canvas-content">
                    <div ref="canvas" id="canvas-container" />
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
        <SidePanel id="right" side="right">
            <template v-slot:panel>
                <EditorPanel
                    :id="id"
                    :name="name"
                    :tags="tags"
                    :parameters="parameters"
                    :annotation="annotation"
                    :version="currentVersion"
                    :versions="versions"
                    @onVersion="onVersion"
                    @onRename="onRename"
                >
                    <template v-slot:buttons>
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
                    </template>
                </EditorPanel>
            </template>
        </SidePanel>
    </div>
</template>

<script>
import { getDatatypes, getModule, getVersions, saveWorkflow, loadWorkflow } from "./services";
import {
    showWarnings,
    showUpgradeMessage,
    copyIntoWorkflow,
    getWorkflowParameters,
    showAttributes,
    showForm,
    saveAs
} from "./utilities";
import WorkflowManager from "mvc/workflow/workflow-manager";
import WorkflowOptions from "./Options";
import MarkdownEditor from "components/Markdown/MarkdownEditor";
import ToolBoxWorkflow from "components/Panels/ToolBoxWorkflow";
import SidePanel from "components/Panels/SidePanel";
import { getAppRoot } from "onload/loadConfig";
import reportDefault from "./reportDefault";
import { showReportHelp } from "./reportHelp";
import EditorPanel from "./EditorPanel";
import { hide_modal, show_message } from "layout/modal";

export default {
    components: {
        MarkdownEditor,
        WorkflowOptions,
        SidePanel,
        ToolBoxWorkflow,
        EditorPanel
    },
    props: {
        id: {
            type: String
        },
        version: {
            type: Number
        },
        name: {
            type: String
        },
        tags: {
            type: Array
        },
        annotation: {
            type: String
        },
        module_sections: {
            type: Array
        },
        data_managers: {
            type: Array
        },
        workflows: {
            type: Array
        },
        toolbox: {
            type: Array
        }
    },
    data() {
        return {
            isCanvas: true,
            versions: [],
            currentVersion: this.version,
            parameters: []
        };
    },
    created() {
        getDatatypes().then(response => {
            const datatypes = response.datatypes;
            const datatypes_mapping = response.datatypes_mapping;
            this.manager = new WorkflowManager({ datatypes_mapping }, this.$refs.canvas);
            this.manager
                .on("onClearActiveNode", () => {
                    showAttributes();
                })
                .on("onActiveNode", (form, node) => {
                    showForm(this.manager, form, node, datatypes);
                })
                .on("onNodeChange", (form, node) => {
                    this.parameters = getWorkflowParameters(this.manager.nodes);
                    showForm(this.manager, form, node, datatypes);
                });
            this.loadCurrent(this.id, this.version);
        });
    },
    methods: {
        onInsertTool(tool_id, tool_name) {
            var node = this.manager.create_node("tool", tool_name, tool_id);
            const requestData = {
                type: "tool",
                tool_id: tool_id,
                _: "true"
            };
            getModule(requestData).then(response => {
                this.manager.set_node(node, response);
            });
        },
        onInsertModule(module_id, module_name) {
            var node = this.manager.create_node(module_id, module_name);
            const requestData = {
                type: module_id,
                _: "true"
            };
            getModule(requestData).then(response => {
                this.manager.set_node(node, response);
            });
        },
        onInsertWorkflow(workflow_id, workflow_name) {
            var node = this.manager.create_node("tool", workflow_name, workflow_id);
            const requestData = {
                type: "subworkflow",
                content_id: workflow_id,
                _: "true"
            };
            getModule(requestData).then(response => {
                this.manager.set_node(node, response);
            });
        },
        onInsertWorkflowSteps(workflow_id, step_count) {
            copyIntoWorkflow(this.manager, workflow_id, step_count);
        },
        onDownload() {
            window.location = `${getAppRoot()}api/workflows/${this.id}/download?format=json-download`;
        },
        onSaveAs() {
            saveAs(this.manager);
        },
        onLayout() {
            this.manager.layout_auto();
        },
        onAttributes() {
            this.manager.clear_active_node();
        },
        onEdit() {
            this.isCanvas = true;
        },
        onReport() {
            this.isCanvas = false;
        },
        onRename(name) {
            this.name = name;
        },
        onReportUpdate(markdown) {
            this.manager.has_changes = true;
            this.manager.report.markdown = markdown;
        },
        onRun() {
            window.location = `${getAppRoot()}workflows/run?id=${this.id}`;
        },
        onSave() {
            show_message("Saving workflow...", "progress");
            saveWorkflow(this.manager, this.id)
                .then(data => {
                    showWarnings(data);
                    getVersions(this.id).then(versions => {
                        this.versions = versions;
                        hide_modal();
                    });
                })
                .catch(response => {
                    hide_modal();
                    alert("Saving workflow failed.");
                });
        },
        onReportHelp() {
            showReportHelp();
        },
        onVersion(version) {
            if (version != this.manager.workflow_version) {
                if (this.manager.has_changes) {
                    const r = window.confirm(
                        "There are unsaved changes to your workflow which will be lost. Continue ?"
                    );
                    if (r == false) {
                        this.currentVersion = this.manager.workflow_version;
                        return;
                    }
                }
                this.currentVersion = version;
                this.loadCurrent(this.id, version);
            }
        },
        loadCurrent(id, version) {
            show_message("Loading workflow...", "progress");
            loadWorkflow(this.manager, id, version)
                .then(data => {
                    const report = data.report || {};
                    const markdown = report.markdown || reportDefault;
                    this.$refs["report-editor"].input = markdown;
                    showUpgradeMessage(this.manager, data);
                    getVersions(this.id).then(versions => {
                        this.versions = versions;
                    });
                })
                .catch(response => {
                    hide_modal();
                    alert("Loading workflow failed.");
                });
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
