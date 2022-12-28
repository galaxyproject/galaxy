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
                <workflow-graph
                    v-if="!datatypesMapperLoading"
                    :steps="steps"
                    :datatypes-mapper="datatypesMapper"
                    :get-manager="getManager"
                    :nodes="nodes"
                    @transform="(value) => (transform = value)"
                    @graph-offset="(value) => (graphOffset = value)"
                    @onUpdate="onUpdate"
                    @onClone="onClone"
                    @onCreate="onInsertTool"
                    @onChange="onChange"
                    @onConnect="onConnect"
                    @onDisconnect="onDisconnect"
                    @onRemove="onRemove"
                    @onUpdateStep="onUpdateStep"
                    @onUpdateStepPosition="onUpdateStepPosition">
                </workflow-graph>
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
                        <div ref="right-panel" class="unified-panel-body workflow-right p-2">
                            <div>
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
                                <workflow-text :steps="steps" @new-steps="onNewSteps" />
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
import { fromSimple, toSimple } from "./modules/model";
import { getModule, getVersions, saveWorkflow, loadWorkflow } from "./modules/services";
import { getUntypedWorkflowParameters } from "./modules/parameters";
import { getStateUpgradeMessages } from "./modules/utilities";
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
import WorkflowGraph from "./WorkflowGraph.vue";
import WorkflowText from "./WorkflowText";
import { defaultPosition } from "./composables/useDefaultStepPosition";
import { useConnectionStore } from "@/stores/workflowConnectionStore";

import Vue, { onUnmounted } from "vue";
import { ConfirmDialog } from "composables/confirmDialog";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { storeToRefs } from "pinia";
import { useDatatypesMapper } from "@/composables/datatypesMapper";

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
        WorkflowLint,
        WorkflowText,
        RefactorConfirmationModal,
        MessagesModal,
        WorkflowGraph,
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
    setup() {
        const { datatypes, datatypesMapper, datatypesMapperLoading } = useDatatypesMapper();
        const connectionsStore = useConnectionStore();
        const stepStore = useWorkflowStepStore();
        const { getStepIndex, steps } = storeToRefs(stepStore);
        const stateStore = useWorkflowStateStore();
        const { nodes, activeNode, activeNodeId } = storeToRefs(stateStore);
        function resetStores() {
            connectionsStore.$reset();
            stepStore.$reset();
            stateStore.$reset();
        }
        onUnmounted(() => {
            resetStores();
        });
        return {
            connectionsStore,
            stepStore,
            steps: steps,
            nodeIndex: getStepIndex,
            datatypes,
            activeNode,
            activeNodeId,
            nodes,
            datatypesMapper,
            datatypesMapperLoading,
            stateStore,
            resetStores,
        };
    },
    data() {
        return {
            isCanvas: true,
            markdownConfig: null,
            markdownText: null,
            versions: [],
            parameters: null,
            hasChanges: false,
            report: {},
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
            saveAsName: null,
            saveAsAnnotation: null,
            showSaveAsModal: false,
            transform: { x: 0, y: 0, k: 1 },
            graphOffset: { left: 0, top: 0, width: 0 },
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
        activeNodeName() {
            return this.activeNode?.name;
        },
        activeNodeContentId() {
            return this.activeNode && this.activeNode.contentId;
        },
        activeNodeLabel() {
            return this.steps[this.activeNodeId]?.label;
        },
        activeNodeAnnotation() {
            return this.steps[this.activeNodeId]?.annotation;
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
    },
    watch: {
        id(newId, oldId) {
            if (oldId) {
                this._loadCurrent(newId);
            }
        },
        annotation(newAnnotation, oldAnnotation) {
            if (newAnnotation != oldAnnotation) {
                this.hasChanges = true;
            }
        },
        name(newName, oldName) {
            if (newName != oldName) {
                this.hasChanges = true;
            }
        },
        steps(newSteps, oldSteps) {
            this.hasChanges = true;
        },
        hasChanges() {
            this.$emit("update:confirmation", this.hasChanges);
        },
    },
    created() {
        this.lastQueue = new LastQueue();
        this._loadCurrent(this.id, this.version);
        hide_modal();
    },
    methods: {
        onNewSteps(newSteps) {
            Object.entries(newSteps).map(([_, step]) => {
                this.stepStore.addStep(step);
            });
        },
        onUpdateStep(step) {
            this.stepStore.updateStep(step);
            this.hasChanges = true;
        },
        onUpdateStepPosition(stepId, position) {
            const step = { ...this.steps[stepId], position };
            this.onUpdateStep(step);
        },
        onConnect(connection) {
            this.connectionsStore.addConnection(connection);
        },
        onDisconnect(nodeId, inputName) {
            // delete this.steps[nodeId].input_connections[inputName];
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
        onUpdate(node) {
            getModule({
                type: node.type,
                content_id: node.contentId,
                _: "true",
            }).then((response) => {
                // TODO: state, inputs and outputs should go to store and data should flow from there,
                // but complicated by mixing state and presentation details
                this.onUpdateStep({
                    ...this.steps[node.id],
                    tool_state: response.tool_state,
                    inputs: response.inputs,
                    outputs: response.outputs,
                    config_form: response.config_form,
                });
                const newData = { ...this.steps[node.id] };
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
            const updatedStep = { ...this.steps[nodeId], post_job_actions: postJobActions };
            this.stepStore.updateStep(updatedStep);
            this.onChange();
        },
        onRemove(nodeId) {
            this.stepStore.removeStep(nodeId);
            this.showInPanel = "attributes";
        },
        onEditSubworkflow(contentId) {
            const editUrl = `/workflows/edit?workflow_id=${contentId}`;
            this.onNavigate(editUrl);
        },
        async onClone(node) {
            const stepCopy = JSON.parse(JSON.stringify(node.step));
            const { id } = this.stepStore.addStep({
                ...stepCopy,
                uuid: null,
                label: null,
                config_form: JSON.parse(JSON.stringify(node.config_form)),
                annotation: JSON.parse(JSON.stringify(node.annotation)),
                tool_state: JSON.parse(JSON.stringify(node.tool_state)),
                post_job_actions: JSON.parse(JSON.stringify(node.postJobActions)),
            });
            this.stateStore.setActiveNode(id);
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
            loadWorkflow({ workflow: this, id, appendData: true }).then((data) => {
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
                const confirmed = await ConfirmDialog.confirm(
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
                    this.onNavigate(`${getAppRoot()}workflows/edit?id=${response.data}`, true);
                })
                .catch((response) => {
                    this.onWorkflowError("Saving workflow failed, please contact an administrator.");
                });
        },
        onSaveAs() {
            this.showSaveAsModal = true;
        },
        onLayout() {
            // this.canvasManager.drawOverview();
            // this.canvasManager.scrollToNodes();
            return import(/* webpackChunkName: "workflowLayout" */ "./modules/layout.ts").then((layout) => {
                layout.autoLayout(this.steps).then((newSteps) => {
                    newSteps.map((step) => this.onUpdateStep(step));
                });
            });
        },
        onAttributes() {
            this._ensureParametersSet();
            this.stateStore.setActiveNode(null);
            this.showInPanel = "attributes";
        },
        onWorkflowTextEditor() {
            this.stateStore.setActiveNode(null);
            this.showInPanel = "attributes";
        },
        onAnnotation(nodeId, newAnnotation) {
            const step = { ...this.steps[nodeId], annotation: newAnnotation };
            this.onUpdateStep(step);
        },
        onSetData(nodeId, newData) {
            const node = this.nodes[nodeId];
            this.lastQueue.enqueue(getModule, newData).then((data) => {
                // TODO: change data in store, don't change node ...
                // also check that PJAs and other modification survive, or limit to input/output ?
                const step = {
                    ...this.steps[nodeId],
                    inputs: data.inputs,
                    outputs: data.outputs,
                    config_form: data.config_form,
                    tool_state: data.tool_state,
                };
                this.onUpdateStep(step);
                node.setData(data);
            });
        },
        onLabel(nodeId, newLabel) {
            const step = { ...this.steps[nodeId], label: newLabel };
            this.onUpdateStep(step);
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
            const runUrl = `/workflows/run?id=${this.id}`;
            this.onNavigate(runUrl);
        },
        onNavigate(url) {
            this.onSave(true).then(() => {
                this.hasChanges = false;
                this.$router.push(url);
            });
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
            this.stepStore.addStep({
                inputs: [],
                input_connections: {},
                name: name,
                content_id: contentId,
                type: type,
                position: defaultPosition(this.graphOffset, this.transform),
            });
            this.stateStore.setActiveNode(this.nodeIndex);
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
            this.hasChanges = has_changes;
        },
        _loadCurrent(id, version) {
            this.resetStores();
            this.onWorkflowMessage("Loading workflow...", "progress");
            this.lastQueue
                .enqueue(loadWorkflow, { id, version, workflow: this })
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
        onActiveNode(nodeId) {
            this.activeNode = this.nodes[nodeId];
            this.$refs["right-panel"].scrollTop = 0;
        },
        getManager() {
            return this;
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
