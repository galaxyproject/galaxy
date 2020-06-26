<template>
    <div id="columns" class="workflow-client">
        <SidePanel id="left" side="left">
            <template v-slot:panel>
                <ToolBoxWorkflow
                    :toolbox="toolbox"
                    :module-sections="moduleSections"
                    :data-managers="dataManagers"
                    :workflows="workflows"
                    @onInsertTool="onInsertTool"
                    @onInsertModule="onInsertModule"
                    @onInsertWorkflow="onInsertWorkflow"
                    @onInsertWorkflowSteps="onInsertWorkflowSteps"
                />
            </template>
        </SidePanel>
        <div id="center" class="workflow-center inbound">
            <div class="unified-panel-header" unselectable="on">
                <div class="unified-panel-header-inner">
                    <span class="sr-only">Workflow Editor</span>
                    {{ name }}
                </div>
            </div>
            <div id="workflow-canvas" class="unified-panel-body workflow-canvas" v-show="isCanvas">
                <ZoomControl :zoom-level="zoomLevel" @onZoom="onZoom" />
                <div id="canvas-viewport">
                    <div ref="canvas" id="canvas-container" />
                </div>
                <div class="workflow-overview" aria-hidden="true">
                    <div class="workflow-overview-body">
                        <div id="overview-container">
                            <canvas width="0" height="0" id="overview-canvas" />
                            <div id="overview-viewport" />
                        </div>
                    </div>
                </div>
            </div>
            <div class="unified-panel-body workflow-report-body" v-show="!isCanvas">
                <MarkdownEditor ref="report-editor" initial-markdown="" :onupdate="onReportUpdate" :toolbar="false" />
            </div>
        </div>
        <SidePanel id="right" side="right">
            <template v-slot:panel>
                <EditorPanel :canvas="isCanvas" class="workflow-panel">
                    <template v-slot:attributes>
                        <WorkflowAttributes
                            :id="id"
                            :name="name"
                            :tags="tags"
                            :parameters="parameters"
                            :annotation="annotation"
                            :version="version"
                            :versions="versions"
                            @onVersion="onVersion"
                            @onRename="onRename"
                        />
                    </template>
                    <template v-slot:buttons>
                        <WorkflowOptions
                            :canvas="isCanvas"
                            @onSave="onSave"
                            @onSaveAs="onSaveAs"
                            @onRun="onRun"
                            @onDownload="onDownload"
                            @onReport="onReport"
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
    saveAs,
} from "./utilities";
import WorkflowManager from "mvc/workflow/workflow-manager";
import WorkflowOptions from "./Options";
import MarkdownEditor from "components/Markdown/MarkdownEditor";
import ToolBoxWorkflow from "components/Panels/ToolBoxWorkflow";
import SidePanel from "components/Panels/SidePanel";
import { getAppRoot } from "onload/loadConfig";
import reportDefault from "./reportDefault";
import EditorPanel from "./EditorPanel";
import { hide_modal, show_message, show_modal } from "layout/modal";
import WorkflowAttributes from "./Attributes";
import ZoomControl from "./ZoomControl";

export default {
    components: {
        EditorPanel,
        MarkdownEditor,
        SidePanel,
        ToolBoxWorkflow,
        WorkflowOptions,
        WorkflowAttributes,
        ZoomControl,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        version: {
            type: Number,
            required: true,
        },
        name: {
            type: String,
            required: true,
        },
        tags: {
            type: Array,
            required: true,
        },
        annotation: {
            type: String,
            required: true,
        },
        moduleSections: {
            type: Array,
            required: true,
        },
        dataManagers: {
            type: Array,
            required: true,
        },
        workflows: {
            type: Array,
            required: true,
        },
        toolbox: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            isCanvas: true,
            versions: [],
            parameters: [],
            zoomLevel: 7,
        };
    },
    created() {
        getDatatypes().then((response) => {
            const datatypes = response.datatypes;
            const datatypes_mapping = response.datatypes_mapping;
            this.manager = new WorkflowManager({ datatypes_mapping }, this.$refs.canvas);
            this.manager
                .on("onRemoveNode", () => {
                    showAttributes();
                })
                .on("onActiveNode", (node) => {
                    showForm(this.manager, node, datatypes);
                })
                .on("onNodeChange", () => {
                    this.parameters = getWorkflowParameters(this.manager.nodes);
                });
            this.loadCurrent(this.id, this.version);
        });
    },
    methods: {
        onInsertTool(tool_id, tool_name) {
            if (!this.isCanvas) {
                this.isCanvas = true;
                return;
            }
            var node = this.manager.create_node("tool", tool_name, tool_id);
            const requestData = {
                type: "tool",
                tool_id: tool_id,
                _: "true",
            };
            getModule(requestData).then((response) => {
                this.manager.set_node(node, response);
            });
        },
        onInsertModule(module_id, module_name) {
            if (!this.isCanvas) {
                this.isCanvas = true;
                return;
            }
            var node = this.manager.create_node(module_id, module_name);
            const requestData = {
                type: module_id,
                _: "true",
            };
            getModule(requestData).then((response) => {
                this.manager.set_node(node, response);
            });
        },
        onInsertWorkflow(workflow_id, workflow_name) {
            if (!this.isCanvas) {
                this.isCanvas = true;
                return;
            }
            var node = this.manager.create_node("subworkflow", workflow_name, workflow_id);
            const requestData = {
                type: "subworkflow",
                content_id: workflow_id,
                _: "true",
            };
            getModule(requestData).then((response) => {
                this.manager.set_node(node, response);
            });
        },
        onInsertWorkflowSteps(workflow_id, step_count) {
            if (!this.isCanvas) {
                this.isCanvas = true;
                return;
            }
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
            showAttributes();
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
        onZoom(zoomLevel) {
            this.zoomLevel = this.manager.canvas_manager.setZoom(zoomLevel);
        },
        onSave() {
            show_message("Saving workflow...", "progress");
            saveWorkflow(this.manager, this.id)
                .then((data) => {
                    showWarnings(data);
                    getVersions(this.id).then((versions) => {
                        this.versions = versions;
                        hide_modal();
                    });
                })
                .catch((response) => {
                    show_modal("Saving workflow failed...", response, { Ok: hide_modal });
                });
        },
        onVersion(version) {
            if (version != this.manager.workflow_version) {
                if (this.manager.has_changes) {
                    const r = window.confirm(
                        "There are unsaved changes to your workflow which will be lost. Continue ?"
                    );
                    if (r == false) {
                        this.version = this.manager.workflow_version;
                        return;
                    }
                }
                this.version = version;
                this.loadCurrent(this.id, version);
            }
        },
        loadCurrent(id, version) {
            show_message("Loading workflow...", "progress");
            loadWorkflow(this.manager, id, version)
                .then((data) => {
                    const report = data.report || {};
                    const markdown = report.markdown || reportDefault;
                    this.$refs["report-editor"].input = markdown;
                    showUpgradeMessage(this.manager, data);
                    getVersions(this.id).then((versions) => {
                        this.versions = versions;
                    });
                })
                .catch((response) => {
                    show_modal("Loading workflow failed...", response, { Ok: hide_modal });
                });
        },
    },
};
</script>
