<template>
    <div id="columns" class="workflow-client">
        <StateUpgradeModal :state-messages="stateMessages" />
        <StateUpgradeModal
            :state-messages="insertedStateMessages"
            title="Subworkflow embedded with changes"
            message="Problems were encountered loading this workflow (possibly a result of tool upgrades). Please review the following parameters and then save." />
        <RefactorConfirmationModal
            :workflow-id="id"
            :refactor-actions="refactorActions"
            @onWorkflowError="onWorkflowError"
            @onWorkflowMessage="onWorkflowMessage"
            @onRefactor="onRefactor"
            @onShow="hideModal" />
        <MessagesModal :title="messageTitle" :message="messageBody" :error="messageIsError" @onHidden="resetMessage" />
        <b-modal
            v-model="showSaveAsModal"
            title="Save As a New Workflow"
            ok-title="Save"
            cancel-title="Cancel"
            @ok="doSaveAs">
            <b-form-group label="Name">
                <b-form-input v-model="saveAsName" />
            </b-form-group>
            <b-form-group label="Annotation">
                <b-form-textarea v-model="saveAsAnnotation" />
            </b-form-group>
        </b-modal>
        <MarkdownEditor
            v-if="!isCanvas"
            :markdown-text="markdownText"
            :markdown-config="markdownConfig"
            :title="'Workflow Report: ' + name"
            :get-manager="getManager"
            @onUpdate="onReportUpdate">
            <template v-slot:buttons>
                <b-button
                    id="workflow-canvas-button"
                    v-b-tooltip.hover.bottom
                    title="Return to Workflow"
                    variant="link"
                    role="button"
                    @click="onEdit">
                    <span class="fa fa-times" />
                </b-button>
            </template>
        </MarkdownEditor>
        <div v-show="isCanvas">
            <SidePanel id="left" side="left">
                <template v-slot:panel>
                    <ProviderAwareToolBoxWorkflow
                        :module-sections="moduleSections"
                        :data-managers="dataManagers"
                        :workflows="workflows"
                        @onInsertTool="onInsertTool"
                        @onInsertModule="onInsertModule"
                        @onInsertWorkflow="onInsertWorkflow"
                        @onInsertWorkflowSteps="onInsertWorkflowSteps" />
                </template>
            </SidePanel>
            <div id="center" class="workflow-center">
                <div class="unified-panel-header" unselectable="on">
                    <div class="unified-panel-header-inner">
                        <span class="sr-only">Workflow Editor</span>
                        {{ name }}
                    </div>
                </div>
                <div id="workflow-canvas" class="unified-panel-body workflow-canvas">
                    <ZoomControl v-if="!checkWheeled" :zoom-level="zoomLevel" @onZoom="onZoom" />
                    <b-button
                        v-else
                        v-b-tooltip.hover
                        class="reset-wheel"
                        variant="light"
                        title="Show Zoom Buttons"
                        size="sm"
                        aria-label="Show Zoom Buttons"
                        @click="resetWheel">
                        Zoom Controls
                    </b-button>
                    <div id="canvas-viewport">
                        <div id="canvas-container" ref="canvas">
                            <WorkflowNode
                                v-for="(step, key) in steps"
                                :id="key"
                                :key="key"
                                :name="step.name"
                                :type="step.type"
                                :content-id="step.content_id"
                                :step="step"
                                :datatypes-mapper="datatypesMapper"
                                :get-manager="getManager"
                                :get-canvas-manager="getCanvasManager"
                                @onAdd="onAdd"
                                @onUpdate="onUpdate"
                                @onClone="onClone"
                                @onCreate="onInsertTool"
                                @onChange="onChange"
                                @onActivate="onActivate"
                                @onRemove="onRemove" />
                        </div>
                    </div>
                    <div class="workflow-overview" aria-hidden="true">
                        <div class="workflow-overview-body">
                            <div id="overview-container">
                                <canvas id="overview-canvas" width="0" height="0" />
                                <div id="overview-viewport" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <SidePanel id="right" side="right">
                <template v-slot:panel>
                    <div class="unified-panel workflow-panel">
                        <div class="unified-panel-header" unselectable="on">
                            <div class="unified-panel-header-inner">
                                <WorkflowOptions
                                    :has-changes="hasChanges"
                                    @onSave="onSave"
                                    @onSaveAs="onSaveAs"
                                    @onRun="onRun"
                                    @onDownload="onDownload"
                                    @onReport="onReport"
                                    @onLayout="onLayout"
                                    @onEdit="onEdit"
                                    @onAttributes="onAttributes"
                                    @onLint="onLint"
                                    @onUpgrade="onUpgrade" />
                            </div>
                        </div>
                        <div ref="right-panel" class="unified-panel-body workflow-right">
                            <div class="m-2">
                                <FormTool
                                    v-if="hasActiveNodeTool"
                                    :key="activeNodeId"
                                    :get-manager="getManager"
                                    :node-id="activeNodeId"
                                    :node-annotation="activeNodeAnnotation"
                                    :node-label="activeNodeLabel"
                                    :node-inputs="activeNodeInputs"
                                    :node-outputs="activeNodeOutputs"
                                    :node-active-outputs="activeNodeActiveOutputs"
                                    :config-form="activeNodeConfigForm"
                                    :datatypes="datatypes"
                                    :post-job-actions="postJobActions"
                                    @onChangePostJobActions="onChangePostJobActions"
                                    @onAnnotation="onAnnotation"
                                    @onLabel="onLabel"
                                    @onSetData="onSetData" />
                                <FormDefault
                                    v-else-if="hasActiveNodeDefault"
                                    :node-name="activeNodeName"
                                    :node-id="activeNodeId"
                                    :node-content-id="activeNodeContentId"
                                    :node-annotation="activeNodeAnnotation"
                                    :node-label="activeNodeLabel"
                                    :node-type="activeNodeType"
                                    :node-outputs="activeNodeOutputs"
                                    :node-active-outputs="activeNodeActiveOutputs"
                                    :config-form="activeNodeConfigForm"
                                    :get-manager="getManager"
                                    :datatypes="datatypes"
                                    @onAnnotation="onAnnotation"
                                    @onLabel="onLabel"
                                    @onEditSubworkflow="onEditSubworkflow"
                                    @onAttemptRefactor="onAttemptRefactor"
                                    @onSetData="onSetData" />
                                <WorkflowAttributes
                                    v-else-if="showAttributes"
                                    :id="id"
                                    :tags="tags"
                                    :parameters="parameters"
                                    :annotation-current.sync="annotation"
                                    :annotation="annotation"
                                    :name-current.sync="name"
                                    :name="name"
                                    :version="version"
                                    :versions="versions"
                                    :license="license"
                                    :creator="creator"
                                    @onVersion="onVersion"
                                    @onLicense="onLicense"
                                    @onCreator="onCreator" />
                                <WorkflowLint
                                    v-else-if="showLint"
                                    :untyped-parameters="parameters"
                                    :annotation="annotation"
                                    :creator="creator"
                                    :license="license"
                                    :get-manager="getManager"
                                    @onAttributes="onAttributes"
                                    @onHighlight="onHighlight"
                                    @onUnhighlight="onUnhighlight"
                                    @onRefactor="onAttemptRefactor"
                                    @onScrollTo="onScrollTo" />
                            </div>
                        </div>
                    </div>
                </template>
            </SidePanel>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import { LastQueue } from "utils/promise-queue";
import { getDatatypesMapper } from "components/Datatypes";
import { fromSimple, toSimple } from "./modules/model";
import { getModule, getVersions, saveWorkflow, loadWorkflow } from "./modules/services";
import { getUntypedWorkflowParameters } from "./modules/parameters";
import { getStateUpgradeMessages } from "./modules/utilities";
import WorkflowCanvas from "./modules/canvas";
import WorkflowOptions from "./Options";
import FormDefault from "./Forms/FormDefault";
import FormTool from "./Forms/FormTool";
import MarkdownEditor from "components/Markdown/MarkdownEditor";
import ProviderAwareToolBoxWorkflow from "components/Panels/ProviderAwareToolBoxWorkflow";
import SidePanel from "components/Panels/SidePanel";
import { getAppRoot } from "onload/loadConfig";
import reportDefault from "./reportDefault";
import WorkflowLint from "./Lint";
import StateUpgradeModal from "./StateUpgradeModal";
import RefactorConfirmationModal from "./RefactorConfirmationModal";
import MessagesModal from "./MessagesModal";
import { hide_modal } from "layout/modal";
import WorkflowAttributes from "./Attributes";
import ZoomControl from "./ZoomControl";
import WorkflowNode from "./Node";
import Vue from "vue";

export default {
    components: {
        MarkdownEditor,
        SidePanel,
        StateUpgradeModal,
        ProviderAwareToolBoxWorkflow,
        FormDefault,
        FormTool,
        WorkflowOptions,
        WorkflowAttributes,
        ZoomControl,
        WorkflowNode,
        WorkflowLint,
        RefactorConfirmationModal,
        MessagesModal,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        initialVersion: {
            type: Number,
            required: true,
        },
        tags: {
            type: Array,
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
    },
    data() {
        return {
            isCanvas: true,
            markdownConfig: null,
            markdownText: null,
            versions: [],
            parameters: null,
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
            license: null,
            creator: null,
            annotation: null,
            name: null,
            stateMessages: [],
            insertedStateMessages: [],
            refactorActions: [],
            messageTitle: null,
            messageBody: null,
            messageIsError: false,
            version: this.initialVersion,
            showInPanel: "attributes",
            isWheeled: false,
            canvasManager: null,
            saveAsName: null,
            saveAsAnnotation: null,
            showSaveAsModal: false,
        };
    },
    computed: {
        showAttributes() {
            return this.showInPanel == "attributes";
        },
        showLint() {
            return this.showInPanel == "lint";
        },
        postJobActions() {
            return this.activeNode.postJobActions;
        },
        activeNodeId() {
            return this.activeNode && this.activeNode.id;
        },
        activeNodeName() {
            return this.activeNode?.name;
        },
        activeNodeContentId() {
            return this.activeNode && this.activeNode.contentId;
        },
        activeNodeLabel() {
            return this.activeNode?.label;
        },
        activeNodeAnnotation() {
            return this.activeNode?.annotation;
        },
        activeNodeConfigForm() {
            return this.activeNode?.config_form;
        },
        activeNodeInputs() {
            return this.activeNode?.inputs;
        },
        activeNodeOutputs() {
            return this.activeNode?.outputs;
        },
        activeNodeActiveOutputs() {
            return this.activeNode?.activeOutputs;
        },
        activeNodeType() {
            return this.activeNode?.type;
        },
        hasActiveNodeDefault() {
            return this.activeNode && this.activeNode.type != "tool";
        },
        hasActiveNodeTool() {
            return this.activeNode && this.activeNode.type == "tool";
        },
        checkWheeled() {
            if (this.canvasManager != null) {
                return this.canvasManager.isWheeled;
            }
            return this.isWheeled;
        },
    },
    watch: {
        annotation: function (newAnnotation, oldAnnotation) {
            if (newAnnotation != oldAnnotation) {
                this.hasChanges = true;
            }
        },
        name: function (newName, oldName) {
            if (newName != oldName) {
                this.hasChanges = true;
            }
        },
        steps: function (newSteps, oldSteps) {
            this.hasChanges = true;
        },
        nodes: function (newNodes, oldNodes) {
            this.hasChanges = true;
        },
    },
    created() {
        this.lastQueue = new LastQueue();
        getDatatypesMapper(false).then((mapper) => {
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
        hide_modal();
    },
    methods: {
        onActivate(node) {
            if (this.activeNode != node) {
                this.onDeactivate();
                node.makeActive();
                this.activeNode = node;
                this.canvasManager.drawOverview();
                this.$refs["right-panel"].scrollTop = 0;
            }
        },
        onDeactivate() {
            if (this.activeNode) {
                this.activeNode.makeInactive();
                this.activeNode = null;
            }
        },
        onAttemptRefactor(actions) {
            if (this.hasChanges) {
                const r = window.confirm(
                    "You've made changes to your workflow that need to be saved before attempting the requested action. Save those changes and continue?"
                );
                if (r == false) {
                    return;
                }
                this.onWorkflowMessage("Saving workflow...", "progress");
                return saveWorkflow(this)
                    .then((data) => {
                        this.refactorActions = actions;
                    })
                    .catch((response) => {
                        this.onWorkflowError("Saving workflow failed, cannot apply requested changes...", response, {
                            Ok: () => {
                                this.hideModal();
                            },
                        });
                    });
            } else {
                this.refactorActions = actions;
            }
        },
        // synchronize modal handling through this object so we can convert it to be
        // be reactive at some point.
        onWorkflowError(message, response) {
            this.messageTitle = message;
            this.messageBody = response.toString();
            this.messageIsError = true;
        },
        onWorkflowMessage(title, body) {
            this.messageTitle = title;
            this.messageBody = body;
            this.messageIsError = false;
        },
        hideModal() {
            this.messageTitle = null;
            this.messageBody = null;
            this.messageIsError = false;
            hide_modal(); // hide other modals created in utilities also...
        },
        async onRefactor(response) {
            await fromSimple(this, response.workflow);
            this._loadEditorData(response.workflow);
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
                newData.workflow_outputs = newData.outputs.map((o) => {
                    return {
                        output_name: o.name,
                        label: o.label,
                    };
                });
                node.setNode(newData);
            });
        },
        onChange() {
            this.hasChanges = true;
        },
        onChangePostJobActions(nodeId, postJobActions) {
            Vue.set(this.nodes[nodeId], "postJobActions", postJobActions);
            this.onChange();
        },
        onRemove(node) {
            delete this.nodes[node.id];
            Vue.delete(this.steps, node.id);
            this.canvasManager.drawOverview();
            this.onDeactivate();
            this.showInPanel = "attributes";
        },
        onEditSubworkflow(contentId) {
            const editUrl = `${getAppRoot()}workflow/editor?workflow_id=${contentId}`;
            this.onNavigate(editUrl);
        },
        async onClone(node) {
            const newId = this.nodeIndex++;
            const stepCopy = JSON.parse(JSON.stringify(node.step));
            await Vue.set(this.steps, newId, {
                ...stepCopy,
                id: newId,
                uuid: null,
                label: null,
                config_form: JSON.parse(JSON.stringify(node.config_form)),
                annotation: JSON.parse(JSON.stringify(node.annotation)),
                tool_state: JSON.parse(JSON.stringify(node.tool_state)),
                post_job_actions: JSON.parse(JSON.stringify(node.postJobActions)),
            });
            this.canvasManager.drawOverview();
            node = this.nodes[newId];
            this.onActivate(node);
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
        copyIntoWorkflow(id = null) {
            // Load workflow definition
            this.onWorkflowMessage("Importing workflow", "progress");
            loadWorkflow(this, id, null, true).then((data) => {
                // Determine if any parameters were 'upgraded' and provide message
                const insertedStateMessages = getStateUpgradeMessages(data);
                this.onInsertedStateMessages(insertedStateMessages);
            });
        },
        async onInsertWorkflowSteps(workflowId, stepCount) {
            if (!this.isCanvas) {
                this.isCanvas = true;
                return;
            }
            if (stepCount < 10) {
                this.copyIntoWorkflow(workflowId);
            } else {
                const confirmed = await this.$bvModal.msgBoxConfirm(
                    `Warning this will add ${stepCount} new steps into your current workflow.  You may want to consider using a subworkflow instead.`
                );
                if (confirmed) {
                    this.copyIntoWorkflow(workflowId);
                }
            }
        },
        onDownload() {
            window.location = `${getAppRoot()}api/workflows/${this.id}/download?format=json-download`;
        },
        doSaveAs() {
            const rename_name = this.saveAsName ?? `SavedAs_${this.name}`;
            const rename_annotation = this.saveAsAnnotation ?? "";

            // This is an old web controller endpoint that wants form data posted...
            const formData = new FormData();
            formData.append("workflow_name", rename_name);
            formData.append("workflow_annotation", rename_annotation);
            formData.append("from_tool_form", true);
            formData.append("workflow_data", JSON.stringify(toSimple(this)));

            axios
                .post(`${getAppRoot()}workflow/save_workflow_as`, formData)
                .then((response) => {
                    this.onWorkflowMessage("Workflow saved as", "success");
                    this.hideModal();
                    this.onNavigate(`${getAppRoot()}workflow/editor?id=${response.data}`, true);
                })
                .catch((response) => {
                    this.onWorkflowError("Saving workflow failed, please contact an administrator.");
                });
        },
        onSaveAs() {
            this.showSaveAsModal = true;
        },
        onLayout() {
            this.canvasManager.drawOverview();
            this.canvasManager.scrollToNodes();
            return import(/* webpackChunkName: "workflowLayout" */ "./modules/layout.js").then((layout) => {
                layout.autoLayout(this);
            });
        },
        onAttributes() {
            this._ensureParametersSet();
            this.onDeactivate();
            this.showInPanel = "attributes";
        },
        onAnnotation(nodeId, newAnnotation) {
            const node = this.nodes[nodeId];
            node.setAnnotation(newAnnotation);
        },
        onSetData(nodeId, newData) {
            const node = this.nodes[nodeId];
            this.lastQueue.enqueue(getModule, newData).then((data) => {
                node.setData(data);
            });
        },
        onLabel(nodeId, newLabel) {
            const node = this.nodes[nodeId];
            node.setLabel(newLabel);
        },
        onScrollTo(nodeId) {
            const node = this.nodes[nodeId];
            this.canvasManager.scrollToNode(node);
            node.onScrollTo();
        },
        onHighlight(nodeId) {
            const node = this.nodes[nodeId];
            node.onHighlight();
        },
        onUnhighlight(nodeId) {
            const node = this.nodes[nodeId];
            node.onUnhighlight();
        },
        onLint() {
            this._ensureParametersSet();
            this.onDeactivate();
            this.showInPanel = "lint";
        },
        onUpgrade() {
            this.onAttemptRefactor([{ action_type: "upgrade_all_steps" }]);
        },
        onEdit() {
            this.isCanvas = true;
        },
        onReport() {
            this.isCanvas = false;
        },
        onReportUpdate(markdown) {
            this.hasChanges = true;
            this.report.markdown = markdown;
            this.markdownText = markdown;
        },
        onRun() {
            const runUrl = `${getAppRoot()}workflows/run?id=${this.id}`;
            this.onNavigate(runUrl);
        },
        onNavigate(url, force = false) {
            if (!force && this.hasChanges) {
                this.onSave(true).then(() => {
                    window.location = url;
                });
            } else {
                if (this.hasChanges) {
                    window.onbeforeunload = false;
                    this.hideModal();
                }
                window.location = url;
            }
        },
        onZoom(zoomLevel) {
            this.zoomLevel = this.canvasManager.setZoom(zoomLevel);
        },
        resetWheel() {
            this.zoomLevel = this.canvasManager.zoomLevel;
            this.canvasManager.isWheeled = false;
        },
        onSave(hideProgress = false) {
            !hideProgress && this.onWorkflowMessage("Saving workflow...", "progress");
            return saveWorkflow(this)
                .then((data) => {
                    getVersions(this.id).then((versions) => {
                        this.versions = versions;
                        this.hideModal();
                    });
                })
                .catch((response) => {
                    this.onWorkflowError("Saving workflow failed...", response, {
                        Ok: () => {
                            this.hideModal();
                        },
                    });
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
        _ensureParametersSet() {
            this.parameters = getUntypedWorkflowParameters(this.nodes);
        },
        _insertStep(contentId, name, type) {
            if (!this.isCanvas) {
                this.isCanvas = true;
                return;
            }
            Vue.set(this.steps, this.nodeIndex++, {
                name: name,
                content_id: contentId,
                type: type,
            });
        },
        async _loadEditorData(data) {
            const report = data.report || {};
            const markdown = report.markdown || reportDefault;
            this.markdownText = markdown;
            this.markdownConfig = report;
            this.hideModal();
            this.stateMessages = getStateUpgradeMessages(data);
            const has_changes = this.stateMessages.length > 0;
            this.license = data.license;
            this.creator = data.creator;
            getVersions(this.id).then((versions) => {
                this.versions = versions;
            });
            await Vue.nextTick();
            this.canvasManager.drawOverview();
            this.canvasManager.scrollToNodes();
            this.hasChanges = has_changes;
        },
        _loadCurrent(id, version) {
            this.onWorkflowMessage("Loading workflow...", "progress");
            loadWorkflow(this, id, version)
                .then((data) => {
                    this._loadEditorData(data);
                })
                .catch((response) => {
                    this.onWorkflowError("Loading workflow failed...", response);
                });
        },
        onLicense(license) {
            if (this.license != license) {
                this.hasChanges = true;
                this.license = license;
            }
        },
        onCreator(creator) {
            if (this.creator != creator) {
                this.hasChanges = true;
                this.creator = creator;
            }
        },
        getManager() {
            return this;
        },
        getCanvasManager() {
            return this.canvasManager;
        },
        getNode() {
            return this.activeNode;
        },
        onInsertedStateMessages(insertedStateMessages) {
            this.insertedStateMessages = insertedStateMessages;
            this.hideModal();
        },
        resetMessage() {
            this.messageTitle = null;
            this.messageBody = null;
            this.messageError = false;
        },
    },
};
</script>
<style scoped>
.workflow-markdown-editor {
    right: 0px !important;
}
.reset-wheel {
    position: absolute;
    left: 1rem;
    bottom: 1rem;
    cursor: pointer;
    z-index: 1002;
}
</style>
