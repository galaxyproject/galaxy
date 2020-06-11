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
                    <div ref="canvas" id="canvas-container">
                        <WorkflowNode v-for="step in steps"
                            :id="step.id"
                            :name="step.name"
                            :type="step.type"
                            :content-id="step.content_id"
                            :step="step"
                            :key="step.id"
                            :get-manager="getManager"
                            @onAddNode="onAddNode"
                            @onAddClone="onAddClone"
                            @onInsertTool="onInsertTool"
                            @onChange="onChange"
                        />
                    </div>
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
import { getDatatypes, getModule, getVersions, saveWorkflow, loadWorkflow } from "./modules/services";
import {
    showWarnings,
    showUpgradeMessage,
    copyIntoWorkflow,
    getWorkflowParameters,
    showAttributes,
    showForm,
    saveAs,
} from "./modules/utilities";
import WorkflowManager from "./modules/manager";
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
import WorkflowNode from "./Node";

export default {
    components: {
        EditorPanel,
        MarkdownEditor,
        SidePanel,
        ToolBoxWorkflow,
        WorkflowOptions,
        WorkflowAttributes,
        ZoomControl,
        WorkflowNode,
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
            default: "",
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
            steps: [],
            hasChanges: false,
            nodeIndex: 0,
            nodes: {},
        };
    },
    created() {
        getDatatypes().then((response) => {
            const datatypes = response.datatypes;
            const datatypes_mapping = response.datatypes_mapping;
            const nodes = this.nodes;
            this.manager = new WorkflowManager({ datatypes_mapping, nodes }, this.$refs.canvas);
            this.manager
                .on("onRemoveNode", () => {
                    showAttributes();
                })
                .on("onActiveNode", (node) => {
                    showForm(this.manager, node, datatypes);
                });
            this.loadCurrent(this.id, this.version);
        });
    },
    methods: {
        onChange() {
            this.hasChanges = true;
        },
        onAddNode(node) {
            if (node.step.uuid) {
                node.initData(node.step);
                node.updateData(node.step);
            } else {
                getModule({
                    type: node.type,
                    content_id: node.contentId,
                    _: "true",
                }).then((response) => {
                    const newData = Object.assign({}, response, node.step);
                    this.manager.setNode(node, newData);
                });
            }
            this.nodes[node.id] = node;
        },
        onAddClone(node) {
            this.steps.push({
                ...node.step,
                id: this.nodeIndex++,
                annotation: node.annotation,
                tool_state: node.tool_state,
                post_job_actions: node.postJobActions,
            });
        },
        onInsertTool(tool_id, tool_name) {
            if (!this.isCanvas) {
                this.isCanvas = true;
                return;
            }
            this.steps.push({
                id: this.nodeIndex++,
                name: tool_name,
                content_id: tool_id,
                type: "tool",
            });
        },
        onInsertModule(module_id, module_name) {
            if (!this.isCanvas) {
                this.isCanvas = true;
                return;
            }
            this.steps.push({
                id: this.nodeIndex++,
                name: module_name,
                type: module_id,
            });
        },
        onInsertWorkflow(workflow_id, workflow_name) {
            if (!this.isCanvas) {
                this.isCanvas = true;
                return;
            }
            this.steps.push({
                id: this.nodeIndex++,
                name: workflow_name,
                content_id: workflow_id,
                type: "subworkflow",
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
            this.manager.layoutAuto();
        },
        onAttributes() {
            showAttributes();
            this.parameters = getWorkflowParameters(this.manager.nodes);
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
            saveWorkflow(this)
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
            loadWorkflow(this, id, version)
                .then((data) => {
                    const report = data.report || {};
                    const markdown = report.markdown || reportDefault;
                    this.$refs["report-editor"].input = markdown;
                    this.manager.canvas_manager.draw_overview(true);
                    showUpgradeMessage(this.manager, data);
                    getVersions(this.id).then((versions) => {
                        this.versions = versions;
                    });
                })
                .catch((response) => {
                    show_modal("Loading workflow failed...", response, { Ok: hide_modal });
                });
        },
        getManager() {
            return this.manager;
        },
    },
};
</script>
