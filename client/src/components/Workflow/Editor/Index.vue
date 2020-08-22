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
        <div v-if="!isCanvas" id="center" class="workflow-center workflow-markdown-editor">
            <MarkdownEditor
                :markdown-text="markdownText"
                :markdown-config="markdownConfig"
                :title="name"
                :nodes="nodes"
                @onUpdate="onReportUpdate"
            >
                <template v-slot:buttons>
                    <b-button
                        id="workflow-canvas-button"
                        title="Return to Workflow"
                        variant="link"
                        role="button"
                        v-b-tooltip.hover.bottom
                        @click="onEdit"
                    >
                        <span class="fa fa-times" />
                    </b-button>
                </template>
            </MarkdownEditor>
        </div>
        <div id="center" class="workflow-center inbound" v-show="isCanvas">
            <div class="unified-panel-header" unselectable="on">
                <div class="unified-panel-header-inner">
                    <span class="sr-only">Workflow Editor</span>
                    {{ name }}
                </div>
            </div>
            <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
                <ZoomControl :zoom-level="zoomLevel" @onZoom="onZoom" />
                <div id="canvas-viewport">
                    <div ref="canvas" id="canvas-container">
                        <WorkflowNode
                            v-for="(step, key) in steps"
                            :id="key"
                            :name="step.name"
                            :type="step.type"
                            :content-id="step.content_id"
                            :step="step"
                            :key="key"
                            :datatypes-mapper="datatypesMapper"
                            :get-manager="getManager"
                            :get-canvas-manager="getCanvasManager"
                            @onAdd="onAdd"
                            @onUpdate="onUpdate"
                            @onClone="onClone"
                            @onCreate="onInsertTool"
                            @onChange="onChange"
                            @onActivate="onActivate"
                            @onRemove="onRemove"
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
        </div>
        <SidePanel id="right" side="right" v-show="isCanvas">
            <template v-slot:panel>
                <div class="unified-panel workflow-panel">
                    <div class="unified-panel-header" unselectable="on">
                        <div class="unified-panel-header-inner">
                            <WorkflowOptions
                                @onSave="onSave"
                                @onSaveAs="onSaveAs"
                                @onRun="onRun"
                                @onDownload="onDownload"
                                @onReport="onReport"
                                @onLayout="onLayout"
                                @onEdit="onEdit"
                                @onAttributes="onAttributes"
                            />
                        </div>
                    </div>
                    <div class="unified-panel-body workflow-right">
                        <div class="m-1">
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
                            <div id="right-content" class="right-content" />
                        </div>
                    </div>
                </div>
            </template>
        </SidePanel>
    </div>
</template>

<script>
import { getDatatypesMapper } from "components/Datatypes";
import { getModule, getVersions, saveWorkflow, loadWorkflow } from "./modules/services";
import {
    showWarnings,
    showUpgradeMessage,
    copyIntoWorkflow,
    getWorkflowParameters,
    showAttributes,
    showForm,
    saveAs,
} from "./modules/utilities";
import WorkflowCanvas from "./modules/canvas";
import WorkflowOptions from "./Options";
import MarkdownEditor from "components/Markdown/MarkdownEditor";
import ToolBoxWorkflow from "components/Panels/ToolBoxWorkflow";
import SidePanel from "components/Panels/SidePanel";
import { getAppRoot } from "onload/loadConfig";
import reportDefault from "./reportDefault";
import { hide_modal, show_message, show_modal } from "layout/modal";
import WorkflowAttributes from "./Attributes";
import ZoomControl from "./ZoomControl";
import WorkflowNode from "./Node";
import Vue from "vue";

export default {
    components: {
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
            markdownConfig: null,
            markdownText: null,
            versions: [],
            parameters: [],
            zoomLevel: 7,
            steps: {},
            hasChanges: false,
            nodeIndex: 0,
            nodes: {},
            datatypesMapper: null,
            datatypes: [],
            report: {},
            activeNode: null,
            labels: {},
        };
    },
    created() {
        getDatatypesMapper().then((mapper) => {
            this.datatypesMapper = mapper;
            this.datatypes = mapper.datatypes;

            // canvas overview management
            this.canvasManager = new WorkflowCanvas(this, this.$refs.canvas);
            this._loadCurrent(this.id, this.version);
        });

        // Notify user if workflow has not been saved yet
        window.onbeforeunload = () => {
            if (this.hasChanges) {
                return "There are unsaved changes to your workflow which will be lost.";
            }
        };
    },
    methods: {
        onActivate(node) {
            if (this.activeNode != node) {
                if (this.activeNode) {
                    this.activeNode.makeInactive();
                }
                document.activeElement.blur();
                node.makeActive();
                this.activeNode = node;
            }
            showForm(this, node, this.datatypes);
            this.canvasManager.drawOverview();
        },
        onAdd(node) {
            this.nodes[node.id] = node;
        },
        onUpdate(node) {
            getModule({
                type: node.type,
                content_id: node.contentId,
                _: "true",
            }).then((response) => {
                const newData = Object.assign({}, response, node.step);
                node.setNode(newData);
            });
        },
        onChange() {
            this.hasChanges = true;
        },
        onRemove(node) {
            delete this.nodes[node.id];
            Vue.delete(this.steps, node.id);
            this.canvasManager.drawOverview();
            this.activeNode = null;
            this.hasChanges = true;
            showAttributes();
        },
        onClone(node) {
            Vue.set(this.steps, this.nodeIndex++, {
                ...node.step,
                uuid: null,
                annotation: node.annotation,
                tool_state: node.tool_state,
                post_job_actions: node.postJobActions,
            });
        },
        onInsertTool(tool_id, tool_name) {
            this._insertStep(tool_id, tool_name, "tool");
        },
        onInsertModule(module_id, module_name) {
            this._insertStep(null, module_name, module_id);
        },
        onInsertWorkflow(workflow_id, workflow_name) {
            this._insertStep(workflow_id, workflow_name, "subworkflow");
        },
        onInsertWorkflowSteps(workflow_id, step_count) {
            if (!this.isCanvas) {
                this.isCanvas = true;
                return;
            }
            copyIntoWorkflow(this, workflow_id, step_count);
        },
        onDownload() {
            window.location = `${getAppRoot()}api/workflows/${this.id}/download?format=json-download`;
        },
        onSaveAs() {
            saveAs(this);
        },
        onLayout() {
            this.canvasManager.drawOverview();
            this.canvasManager.scrollToNodes();
            return import(/* webpackChunkName: "workflowLayout" */ "./modules/layout.js").then((layout) => {
                layout.autoLayout(this);
            });
        },
        onAttributes() {
            showAttributes();
            this.parameters = getWorkflowParameters(this.nodes);
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
            this.hasChanges = true;
            this.report.markdown = markdown;
            this.markdownText = markdown;
        },
        onRun() {
            const runUrl = `${getAppRoot()}workflows/run?id=${this.id}`;
            if (this.hasChanges) {
                this.onSave(true).then(() => {
                    window.location = runUrl;
                });
            } else {
                window.location = runUrl;
            }
        },
        onZoom(zoomLevel) {
            this.zoomLevel = this.canvasManager.setZoom(zoomLevel);
        },
        onSave(hideProgress = false) {
            !hideProgress && show_message("Saving workflow...", "progress");
            return saveWorkflow(this)
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
            if (version != this.version) {
                if (this.hasChanges) {
                    const r = window.confirm(
                        "There are unsaved changes to your workflow which will be lost. Continue ?"
                    );
                    if (r == false) {
                        return;
                    }
                }
                this.version = version;
                this._loadCurrent(this.id, version);
            }
        },
        _insertStep(conentId, name, type) {
            if (!this.isCanvas) {
                this.isCanvas = true;
                return;
            }
            Vue.set(this.steps, this.nodeIndex++, {
                name: name,
                content_id: conentId,
                type: type,
            });
        },
        _loadCurrent(id, version) {
            show_message("Loading workflow...", "progress");
            loadWorkflow(this, id, version)
                .then((data) => {
                    const report = data.report || {};
                    const markdown = report.markdown || reportDefault;
                    this.markdownText = markdown;
                    this.markdownConfig = report;
                    showUpgradeMessage(data);
                    getVersions(this.id).then((versions) => {
                        this.versions = versions;
                    });
                    Vue.nextTick(() => {
                        this.canvasManager.drawOverview();
                        this.canvasManager.scrollToNodes();
                        this.hasChanges = false;
                    });
                })
                .catch((response) => {
                    show_modal("Loading workflow failed...", response, { Ok: hide_modal });
                });
        },
        getManager() {
            return this;
        },
        getCanvasManager() {
            return this.canvasManager;
        },
    },
};
</script>
<style scoped>
.workflow-markdown-editor {
    right: 0px !important;
}
</style>
