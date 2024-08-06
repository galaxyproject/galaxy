<template>
    <div v-if="isCanvas" id="columns" class="d-flex">
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
        <SaveChangesModal :nav-url.sync="navUrl" :show-modal.sync="showSaveChangesModal" @on-proceed="onNavigate" />
        <b-modal
            v-model="showSaveAsModal"
            title="Save As a New Workflow"
            ok-title="Save"
            cancel-title="Cancel"
            @ok="doSaveAs(false)">
            <b-form-group label="Name">
                <b-form-input v-model="saveAsName" />
            </b-form-group>
            <b-form-group label="Annotation">
                <b-form-textarea v-model="saveAsAnnotation" />
            </b-form-group>
        </b-modal>
        <FlexPanel side="left">
            <ToolPanel
                workflow
                :module-sections="moduleSections"
                :data-managers="dataManagers"
                :editor-workflows="workflows"
                @onInsertTool="onInsertTool"
                @onInsertModule="onInsertModule"
                @onInsertWorkflow="onInsertWorkflow"
                @onInsertWorkflowSteps="onInsertWorkflowSteps" />
        </FlexPanel>
        <div id="center" class="workflow-center">
            <div class="unified-panel-header" unselectable="on">
                <div class="unified-panel-header-inner">
                    <span class="sr-only">Workflow Editor</span>
                    <span>
                        {{ name || "..." }}
                        <i v-if="isNewTempWorkflow">
                            (Click Save <span class="fa fa-floppy-o" /> to create this workflow)
                        </i>
                    </span>
                </div>
            </div>
            <WorkflowGraph
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
            </WorkflowGraph>
        </div>
        <FlexPanel side="right">
            <div class="unified-panel bg-white">
                <div class="unified-panel-header" unselectable="on">
                    <div class="unified-panel-header-inner">
                        <WorkflowOptions
                            :is-new-temp-workflow="isNewTempWorkflow"
                            :has-changes="hasChanges"
                            :has-invalid-connections="hasInvalidConnections"
                            @onSave="onSave"
                            @onCreate="onCreate"
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
                <div ref="rightPanelElement" class="unified-panel-body workflow-right p-2">
                    <div v-if="!initialLoading">
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
                            @onTags="onTags"
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
        </FlexPanel>
    </div>
    <MarkdownEditor
        v-else
        :markdown-text="markdownText"
        :markdown-config="report"
        mode="report"
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
</template>

<script>
import { Toast } from "composables/toast";
import { storeToRefs } from "pinia";
import Vue, { computed, nextTick, onUnmounted, ref, unref, watch } from "vue";

import { getUntypedWorkflowParameters } from "@/components/Workflow/Editor/modules/parameters";
import { ConfirmDialog } from "@/composables/confirmDialog";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { useUid } from "@/composables/utils/uid";
import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import { hide_modal } from "@/layout/modal";
import { getAppRoot } from "@/onload/loadConfig";
import { useScopePointerStore } from "@/stores/scopePointerStore";
import { LastQueue } from "@/utils/lastQueue";
import { errorMessageAsString } from "@/utils/simple-error";

import { Services } from "../services";
import { defaultPosition } from "./composables/useDefaultStepPosition";
import { fromSimple } from "./modules/model";
import { getModule, getVersions, loadWorkflow, saveWorkflow } from "./modules/services";
import { getStateUpgradeMessages } from "./modules/utilities";
import reportDefault from "./reportDefault";

import WorkflowAttributes from "./Attributes.vue";
import WorkflowLint from "./Lint.vue";
import MessagesModal from "./MessagesModal.vue";
import WorkflowOptions from "./Options.vue";
import RefactorConfirmationModal from "./RefactorConfirmationModal.vue";
import SaveChangesModal from "./SaveChangesModal.vue";
import StateUpgradeModal from "./StateUpgradeModal.vue";
import WorkflowGraph from "./WorkflowGraph.vue";
import MarkdownEditor from "@/components/Markdown/MarkdownEditor.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import ToolPanel from "@/components/Panels/ToolPanel.vue";
import FormDefault from "@/components/Workflow/Editor/Forms/FormDefault.vue";
import FormTool from "@/components/Workflow/Editor/Forms/FormTool.vue";

export default {
    components: {
        MarkdownEditor,
        FlexPanel,
        SaveChangesModal,
        StateUpgradeModal,
        ToolPanel,
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
        workflowId: {
            type: String,
            default: undefined,
        },
        initialVersion: {
            type: Number,
            default: undefined,
        },
        workflowTags: {
            type: Array,
            default: () => [],
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

        const uid = unref(useUid("workflow-editor-"));
        const id = ref(props.workflowId || uid);

        const { connectionStore, stepStore, stateStore, commentStore } = provideScopedWorkflowStores(id);

        watch(
            () => stateStore.activeNodeId,
            () => {
                scrollToTop();
            }
        );

        const rightPanelElement = ref(null);

        function scrollToTop() {
            rightPanelElement.value?.scrollTo({
                top: 0,
                behavior: "instant",
            });
        }

        const { comments } = storeToRefs(commentStore);
        const { getStepIndex, steps } = storeToRefs(stepStore);
        const { activeNodeId } = storeToRefs(stateStore);
        const activeStep = computed(() => {
            if (activeNodeId.value !== null) {
                return stepStore.getStep(activeNodeId.value);
            }
            return null;
        });

        const hasChanges = ref(false);
        const initialLoading = ref(true);
        const hasInvalidConnections = computed(() => Object.keys(connectionStore.invalidConnections).length > 0);

        stepStore.$subscribe((_mutation, _state) => {
            if (!initialLoading.value) {
                hasChanges.value = true;
            }
        });

        commentStore.$subscribe((_mutation, _state) => {
            if (!initialLoading.value) {
                hasChanges.value = true;
            }
        });

        async function resetStores() {
            hasChanges.value = false;
            connectionStore.$reset();
            stepStore.$reset();
            stateStore.$reset();
            commentStore.$reset();
            await nextTick();
        }

        onUnmounted(async () => {
            await resetStores();
            emit("update:confirmation", false);
        });

        return {
            id,
            rightPanelElement,
            scrollToTop,
            connectionStore,
            hasChanges,
            hasInvalidConnections,
            stepStore,
            steps,
            comments,
            nodeIndex: getStepIndex,
            datatypes,
            activeStep,
            activeNodeId,
            datatypesMapper,
            datatypesMapperLoading,
            stateStore,
            resetStores,
            initialLoading,
        };
    },
    data() {
        return {
            isCanvas: true,
            markdownText: null,
            versions: [],
            parameters: null,
            report: {},
            labels: {},
            license: null,
            creator: null,
            annotation: null,
            name: "Unnamed Workflow",
            tags: this.workflowTags,
            services: null,
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
            showSaveChangesModal: false,
            navUrl: "",
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
        isNewTempWorkflow() {
            return !this.workflowId;
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
        initialVersion(newVal, oldVal) {
            if (newVal != oldVal && oldVal === undefined) {
                this.version = this.initialVersion;
            }
        },
    },
    async created() {
        this.services = new Services();
        this.lastQueue = new LastQueue();
        await this._loadCurrent(this.id, this.version);
        hide_modal();
        this.initialLoading = false;
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
            this.connectionStore.addConnection(connection);
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
            await this.resetStores();
            await fromSimple(this.id, response.workflow);
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
                    tool_version: response.tool_version,
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
            this.stateStore.activeNodeId = id;
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
                fromSimple(this.id, data, true, defaultPosition(this.graphOffset, this.transform));
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
        async doSaveAs() {
            if (!this.saveAsName && !this.nameValidate()) {
                return;
            }
            const rename_name = this.saveAsName ?? `SavedAs_${this.name}`;
            const rename_annotation = this.saveAsAnnotation ?? "";

            try {
                const newSaveAsWf = { ...this, name: rename_name, annotation: rename_annotation };
                const { id, name, number_of_steps } = await this.services.createWorkflow(newSaveAsWf);
                const message = `Created new workflow '${name}' with ${number_of_steps} steps.`;
                this.hasChanges = false;
                await this.routeToWorkflow(id);
                Toast.success(message);
            } catch (e) {
                const errorHeading = `Saving workflow as '${rename_name}' failed`;
                this.onWorkflowError(errorHeading, errorMessageAsString(e) || "Please contact an administrator.", {
                    Ok: () => {
                        this.hideModal();
                    },
                });
            }
        },
        onSaveAs() {
            this.showSaveAsModal = true;
        },
        onLayout() {
            return import(/* webpackChunkName: "workflowLayout" */ "./modules/layout.ts").then((layout) => {
                layout.autoLayout(this.id, this.steps).then((newSteps) => {
                    newSteps.map((step) => this.onUpdateStep(step));
                });
            });
        },
        onAttributes() {
            this._ensureParametersSet();
            this.stateStore.activeNodeId = null;
            this.showInPanel = "attributes";
        },
        onWorkflowTextEditor() {
            this.stateStore.activeNodeId = null;
            this.showInPanel = "attributes";
        },
        onAnnotation(nodeId, newAnnotation) {
            const step = { ...this.steps[nodeId], annotation: newAnnotation };
            this.onUpdateStep(step);
        },
        async routeToWorkflow(id) {
            // map scoped stores to existing stores, before updating the id
            const { addScopePointer } = useScopePointerStore();
            addScopePointer(id, this.id);

            this.id = id;
            await this.onSave();
            this.hasChanges = false;
            this.$router.replace({ query: { id } });
        },
        async onCreate() {
            if (!this.nameValidate()) {
                return;
            }
            try {
                const { id, name, number_of_steps } = await this.services.createWorkflow(this);
                const message = `Created new workflow '${name}' with ${number_of_steps} steps.`;
                this.hasChanges = false;
                await this.routeToWorkflow(id);
                Toast.success(message);
            } catch (e) {
                this.onWorkflowError(
                    "Creating workflow failed",
                    errorMessageAsString(e) || "Please contact an administrator.",
                    {
                        Ok: () => {
                            this.hideModal();
                        },
                    }
                );
            }
        },
        nameValidate() {
            if (!this.name) {
                Toast.error("Please provide a name for your workflow.");
                this.onAttributes();
                return false;
            }
            return true;
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
                        tool_version: data.tool_version,
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
            this.stateStore.activeNodeId = null;
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
        async onNavigate(url, forceSave = false, ignoreChanges = false) {
            if (this.isNewTempWorkflow) {
                await this.onCreate();
            } else if (this.hasChanges && !forceSave && !ignoreChanges) {
                // if there are changes, prompt user to save or discard or cancel
                this.navUrl = url;
                this.showSaveChangesModal = true;
                return;
            } else if (forceSave) {
                // when forceSave is true, save the workflow before navigating
                await this.onSave();
            }

            this.hasChanges = false;
            await nextTick();
            this.$router.push(url);
        },
        onSave(hideProgress = false) {
            if (!this.nameValidate()) {
                return;
            }
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
            const stepData = this.stepStore.insertNewStep(
                contentId,
                name,
                type,
                defaultPosition(this.graphOffset, this.transform)
            );

            getModule({ name, type, content_id: contentId }, stepData.id, this.stateStore.setLoadingState).then(
                (response) => {
                    this.stepStore.updateStep({
                        ...stepData,
                        tool_state: response.tool_state,
                        inputs: response.inputs,
                        outputs: response.outputs,
                        config_form: response.config_form,
                    });
                    this.stateStore.activeNodeId = stepData.id;
                }
            );
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
            this.report = report;
            this.markdownText = markdown;
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
        async _loadCurrent(id, version) {
            if (!this.isNewTempWorkflow) {
                await this.resetStores();
                this.onWorkflowMessage("Loading workflow...", "progress");

                try {
                    const data = await this.lastQueue.enqueue(loadWorkflow, { id, version });
                    await fromSimple(id, data);
                    await this._loadEditorData(data);
                } catch (e) {
                    this.onWorkflowError("Loading workflow failed...", e);
                }
            }
        },
        onTags(tags) {
            if (this.tags != tags) {
                this.tags = tags;
            }
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
.reset-wheel {
    position: absolute;
    left: 1rem;
    bottom: 1rem;
    cursor: pointer;
    z-index: 2000;
}

.workflow-center {
    z-index: 0;
    display: flex;
    flex-direction: column;
    flex-grow: 1;
    overflow: auto;
    width: 100%;
}
</style>
