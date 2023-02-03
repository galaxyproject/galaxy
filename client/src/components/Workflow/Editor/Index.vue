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
            :steps="steps"
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
                    :highlight-id="highlightId"
                    :scroll-to-id="scrollToId"
                    @scrollTo="scrollToId = null"
                    @transform="(value) => (transform = value)"
                    @graph-offset="(value) => (graphOffset = value)"
                    @onUpdate="onUpdate"
                    @onClone="onClone"
                    @onCreate="onInsertTool"
                    @onChange="onChange"
                    @onConnect="onConnect"
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
                                    :has-invalid-connections="hasInvalidConnections"
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
                                    :key="activeStep.id"
                                    :step="activeStep"
                                    :datatypes="datatypes"
                                    @onChangePostJobActions="onChangePostJobActions"
                                    @onAnnotation="onAnnotation"
                                    @onLabel="onLabel"
                                    @onUpdateStep="onUpdateStep"
                                    @onSetData="onSetData" />
                                <FormDefault
                                    v-else-if="hasActiveNodeDefault"
                                    :step="activeStep"
                                    :datatypes="datatypes"
                                    @onAnnotation="onAnnotation"
                                    @onLabel="onLabel"
                                    @onEditSubworkflow="onEditSubworkflow"
                                    @onAttemptRefactor="onAttemptRefactor"
                                    @onUpdateStep="onUpdateStep"
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
                                    :steps="steps"
                                    :datatypes-mapper="datatypesMapper"
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
import { LastQueue } from "@/utils/promise-queue";
import { fromSimple, toSimple } from "./modules/model";
import { getModule, getVersions, saveWorkflow, loadWorkflow } from "./modules/services";
import { getUntypedWorkflowParameters } from "@/components/Workflow/Editor/modules/parameters";
import { getStateUpgradeMessages } from "./modules/utilities";
import WorkflowOptions from "./Options.vue";
import FormDefault from "@/components/Workflow/Editor/Forms/FormDefault.vue";
import FormTool from "@/components/Workflow/Editor/Forms/FormTool.vue";
import MarkdownEditor from "@/components/Markdown/MarkdownEditor.vue";
import ProviderAwareToolBoxWorkflow from "@/components/Panels/ProviderAwareToolBoxWorkflow.vue";
import SidePanel from "@/components/Panels/SidePanel.vue";
import { getAppRoot } from "@/onload/loadConfig";
import reportDefault from "./reportDefault";
import WorkflowLint from "./Lint.vue";
import StateUpgradeModal from "./StateUpgradeModal.vue";
import RefactorConfirmationModal from "./RefactorConfirmationModal.vue";
import MessagesModal from "./MessagesModal.vue";
import { hide_modal } from "@/layout/modal";
import WorkflowAttributes from "./Attributes.vue";
import WorkflowGraph from "./WorkflowGraph.vue";
import { defaultPosition } from "./composables/useDefaultStepPosition";
import { useConnectionStore } from "@/stores/workflowConnectionStore";

import Vue, { onUnmounted, computed, ref } from "vue";
import { ConfirmDialog } from "@/composables/confirmDialog";
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
    setup(props, { emit }) {
        const { datatypes, datatypesMapper, datatypesMapperLoading } = useDatatypesMapper();
        const connectionsStore = useConnectionStore();
        const stepStore = useWorkflowStepStore();
        const { getStepIndex, steps } = storeToRefs(stepStore);
        const stateStore = useWorkflowStateStore();
        const { activeNodeId } = storeToRefs(stateStore);
        const activeStep = computed(() => {
            if (activeNodeId.value !== null) {
                return stepStore.getStep(activeNodeId.value);
            }
            return null;
        });

        const hasChanges = ref(false);
        const hasInvalidConnections = computed(() => Object.keys(connectionsStore.invalidConnections).length > 0);

        stepStore.$subscribe((mutation, state) => {
            hasChanges.value = true;
        });

        function resetStores() {
            connectionsStore.$reset();
            stepStore.$reset();
            stateStore.$reset();
        }
        onUnmounted(() => {
            resetStores();
            emit("update:confirmation", false);
        });
        return {
            connectionsStore,
            hasChanges,
            hasInvalidConnections,
            stepStore,
            steps,
            nodeIndex: getStepIndex,
            datatypes,
            activeStep,
            activeNodeId,
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
            report: {},
            labels: {},
            license: null,
            creator: null,
            annotation: null,
            name: null,
            stateMessages: [],
            insertedStateMessages: [],
            refactorActions: [],
            scrollToId: null,
            highlightId: null,
            messageTitle: null,
            messageBody: null,
            messageIsError: false,
            version: this.initialVersion,
            showInPanel: "attributes",
            saveAsName: null,
            saveAsAnnotation: null,
            showSaveAsModal: false,
            transform: { x: 0, y: 0, k: 1 },
            graphOffset: { left: 0, top: 0, width: 0, height: 0 },
        };
    },
    computed: {
        showAttributes() {
            return this.showInPanel == "attributes";
        },
        showLint() {
            return this.showInPanel == "lint";
        },
        activeNodeType() {
            return this.activeStep?.type;
        },
        hasActiveNodeDefault() {
            return this.activeStep && this.activeStep?.type != "tool";
        },
        hasActiveNodeTool() {
            return this.activeStep?.type == "tool";
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
        onUpdateStep(step) {
            this.stepStore.updateStep(step);
        },
        onUpdateStepPosition(stepId, position) {
            const step = { ...this.steps[stepId], position };
            this.onUpdateStep(step);
        },
        onConnect(connection) {
            this.connectionsStore.addConnection(connection);
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
            this.resetStores();
            await fromSimple(response.workflow);
            this._loadEditorData(response.workflow);
        },
        onUpdate(step) {
            getModule(
                {
                    type: step.type,
                    content_id: step.contentId,
                    _: "true",
                },
                this.id,
                this.stateStore.setLoadingState
            ).then((response) => {
                this.onUpdateStep({
                    ...this.steps[step.id],
                    config_form: response.config_form,
                    content_id: response.content_id,
                    errors: response.errors,
                    inputs: response.inputs,
                    outputs: response.outputs,
                    tool_state: response.tool_state,
                });
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
        async onClone(stepId) {
            const sourceStep = this.steps[parseInt(stepId)];
            const stepCopy = JSON.parse(JSON.stringify(sourceStep));
            const { id } = this.stepStore.addStep({
                ...stepCopy,
                id: null,
                uuid: null,
                label: null,
                position: defaultPosition(this.graphOffset, this.transform),
            });
            this.stateStore.setActiveNode(id);
        },
        onInsertTool(tool_id, tool_name) {
            this._insertStep(tool_id, tool_name, "tool");
        },
        onInsertModule(module_id, module_name) {
            this._insertStep(module_name, module_name, module_id);
        },
        onInsertWorkflow(workflow_id, workflow_name) {
            this._insertStep(workflow_id, workflow_name, "subworkflow");
        },
        copyIntoWorkflow(id) {
            // Load workflow definition
            this.onWorkflowMessage("Importing workflow", "progress");
            loadWorkflow({ id }).then((data) => {
                fromSimple(data, true, defaultPosition(this.graphOffset, this.transform));
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
        onSetData(stepId, newData) {
            this.lastQueue
                .enqueue(() => getModule(newData, stepId, this.stateStore.setLoadingState))
                .then((data) => {
                    const step = {
                        ...this.steps[stepId],
                        content_id: data.content_id,
                        inputs: data.inputs,
                        outputs: data.outputs,
                        config_form: data.config_form,
                        tool_state: data.tool_state,
                        errors: data.errors,
                    };
                    this.onUpdateStep(step);
                });
        },
        onLabel(nodeId, newLabel) {
            const step = { ...this.steps[nodeId], label: newLabel };
            this.onUpdateStep(step);
        },
        onScrollTo(stepId) {
            this.scrollToId = stepId;
            this.onHighlight(stepId);
        },
        onHighlight(stepId) {
            this.highlightId = stepId;
        },
        onUnhighlight(stepId) {
            this.highlightId = null;
        },
        onLint() {
            this._ensureParametersSet();
            this.stateStore.setActiveNode(null);
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
            this.parameters = getUntypedWorkflowParameters(this.steps);
        },
        _insertStep(contentId, name, type) {
            if (!this.isCanvas) {
                this.isCanvas = true;
                return;
            }
            const stepData = {
                name: name,
                content_id: contentId,
                input_connections: {},
                type: type,
                outputs: [],
                position: defaultPosition(this.graphOffset, this.transform),
                post_job_actions: {},
            };
            const { id } = this.stepStore.addStep(stepData);
            getModule(stepData, id, this.stateStore.setLoadingState).then((response) => {
                this.stepStore.updateStep({
                    ...stepData,
                    tool_state: response.tool_state,
                    inputs: response.inputs,
                    outputs: response.outputs,
                    config_form: response.config_form,
                });
                this.stateStore.setActiveNode(id);
            });
        },
        async _loadEditorData(data) {
            if (data.name !== undefined) {
                this.name = data.name;
            }
            if (data.annotation !== undefined) {
                this.annotation = data.annotation;
            }
            if (data.version !== undefined) {
                this.version = data.version;
            }

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
                .enqueue(loadWorkflow, { id, version })
                .then((data) => {
                    fromSimple(data);
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
            this.$refs["right-panel"].scrollTop = 0;
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
