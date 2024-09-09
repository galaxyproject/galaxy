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
        <ActivityBar
            :default-activities="workflowEditorActivities"
            :special-activities="specialWorkflowActivities"
            activity-bar-id="workflow-editor"
            :show-admin="false"
            @activityClicked="onActivityClicked">
            <template v-slot:side-panel="{ isActiveSideBar }">
                <ToolPanel
                    v-if="isActiveSideBar('workflow-editor-tools')"
                    workflow
                    :module-sections="moduleSections"
                    :data-managers="dataManagers"
                    :editor-workflows="workflows"
                    @onInsertTool="onInsertTool"
                    @onInsertModule="onInsertModule"
                    @onInsertWorkflow="onInsertWorkflow"
                    @onInsertWorkflowSteps="onInsertWorkflowSteps" />
                <WorkflowLint
                    v-else-if="isActiveSideBar('workflow-best-practices')"
                    :untyped-parameters="parameters"
                    :annotation="annotation"
                    :creator="creator"
                    :license="license"
                    :steps="steps"
                    :datatypes-mapper="datatypesMapper"
                    @onAttributes="showAttributes"
                    @onHighlight="onHighlight"
                    @onUnhighlight="onUnhighlight"
                    @onRefactor="onAttemptRefactor"
                    @onScrollTo="onScrollTo" />
                <UndoRedoStack v-else-if="isActiveSideBar('workflow-undo-redo')" :store-id="id" />
                <WorkflowPanel
                    v-else-if="isActiveSideBar('workflow-editor-workflows')"
                    @insertWorkflow="onInsertWorkflow"
                    @insertWorkflowSteps="onInsertWorkflowSteps" />
                <WorkflowAttributes
                    v-else-if="isActiveSideBar('workflow-editor-attributes')"
                    :id="id"
                    :tags="tags"
                    :parameters="parameters"
                    :annotation="annotation"
                    :name="name"
                    :version="version"
                    :versions="versions"
                    :license="license"
                    :creator="creator"
                    @version="onVersion"
                    @tags="setTags"
                    @license="onLicense"
                    @creator="onCreator"
                    @update:nameCurrent="setName"
                    @update:annotationCurrent="setAnnotation" />
            </template>
        </ActivityBar>
        <div id="center" class="workflow-center">
            <div class="editor-top-bar" unselectable="on">
                <span>
                    <span class="sr-only">Workflow Editor</span>
                    <span class="editor-title" :title="name"
                        >{{ name }}
                        <i v-if="hasChanges" class="text-muted"> (unsaved changes) </i>
                    </span>
                </span>

                <b-button-group>
                    <b-button
                        :title="undoRedoStore.undoText + ' (Ctrl + Z)'"
                        :variant="undoRedoStore.hasUndo ? 'secondary' : 'muted'"
                        @click="undoRedoStore.undo()">
                        <FontAwesomeIcon icon="fa-arrow-left" />
                    </b-button>
                    <b-button
                        :title="undoRedoStore.redoText + ' (Ctrl + Shift + Z)'"
                        :variant="undoRedoStore.hasRedo ? 'secondary' : 'muted'"
                        @click="undoRedoStore.redo()">
                        <FontAwesomeIcon icon="fa-arrow-right" />
                    </b-button>
                </b-button-group>
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
                @onClone="onClone"
                @onCreate="onInsertTool"
                @onChange="onChange"
                @onRemove="onRemove"
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
                            :current-active-panel="showInPanel"
                            @onSave="onSave"
                            @onCreate="onCreate"
                            @onSaveAs="onSaveAs"
                            @onRun="onRun"
                            @onDownload="onDownload"
                            @onReport="onReport"
                            @onLayout="onLayout"
                            @onEdit="onEdit"
                            @onAttributes="showAttributes"
                            @onUpgrade="onUpgrade" />
                    </div>
                </div>
                <div ref="rightPanelElement" class="unified-panel-body workflow-right p-2">
                    <div v-if="!initialLoading" class="position-relative h-100">
                        <FormTool
                            v-if="hasActiveNodeTool"
                            :key="activeStep.id"
                            :step="activeStep"
                            :datatypes="datatypes"
                            @onChangePostJobActions="onChangePostJobActions"
                            @onAnnotation="onAnnotation"
                            @onLabel="onLabel"
                            @onSetData="onSetData"
                            @onUpdateStep="updateStep" />
                        <FormDefault
                            v-else-if="hasActiveNodeDefault"
                            :step="activeStep"
                            :datatypes="datatypes"
                            @onAnnotation="onAnnotation"
                            @onLabel="onLabel"
                            @onEditSubworkflow="onEditSubworkflow"
                            @onAttemptRefactor="onAttemptRefactor"
                            @onSetData="onSetData"
                            @onUpdateStep="updateStep" />
                    </div>
                </div>
            </div>
        </FlexPanel>
    </div>
    <MarkdownEditor
        v-else
        :markdown-text="report.markdown"
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
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArrowLeft, faArrowRight, faHistory } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { whenever } from "@vueuse/core";
import { logicAnd, logicNot, logicOr } from "@vueuse/math";
import { Toast } from "composables/toast";
import { storeToRefs } from "pinia";
import Vue, { computed, nextTick, onUnmounted, ref, unref, watch } from "vue";

import { getUntypedWorkflowParameters } from "@/components/Workflow/Editor/modules/parameters";
import { ConfirmDialog } from "@/composables/confirmDialog";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { useMagicKeys } from "@/composables/useMagicKeys";
import { useUid } from "@/composables/utils/uid";
import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import { hide_modal } from "@/layout/modal";
import { getAppRoot } from "@/onload/loadConfig";
import { useScopePointerStore } from "@/stores/scopePointerStore";
import { LastQueue } from "@/utils/lastQueue";
import { errorMessageAsString } from "@/utils/simple-error";

import { Services } from "../services";
import { InsertStepAction, useStepActions } from "./Actions/stepActions";
import { CopyIntoWorkflowAction, SetValueActionHandler } from "./Actions/workflowActions";
import { defaultPosition } from "./composables/useDefaultStepPosition";
import { specialWorkflowActivities, workflowEditorActivities } from "./modules/activities";
import { fromSimple } from "./modules/model";
import { getModule, getVersions, loadWorkflow, saveWorkflow } from "./modules/services";
import { getStateUpgradeMessages } from "./modules/utilities";
import reportDefault from "./reportDefault";

import WorkflowLint from "./Lint.vue";
import MessagesModal from "./MessagesModal.vue";
import WorkflowOptions from "./Options.vue";
import RefactorConfirmationModal from "./RefactorConfirmationModal.vue";
import SaveChangesModal from "./SaveChangesModal.vue";
import StateUpgradeModal from "./StateUpgradeModal.vue";
import WorkflowAttributes from "./WorkflowAttributes.vue";
import WorkflowGraph from "./WorkflowGraph.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import MarkdownEditor from "@/components/Markdown/MarkdownEditor.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import ToolPanel from "@/components/Panels/ToolPanel.vue";
import WorkflowPanel from "@/components/Panels/WorkflowPanel.vue";
import UndoRedoStack from "@/components/UndoRedo/UndoRedoStack.vue";
import FormDefault from "@/components/Workflow/Editor/Forms/FormDefault.vue";
import FormTool from "@/components/Workflow/Editor/Forms/FormTool.vue";

library.add(faArrowLeft, faArrowRight, faHistory);

export default {
    components: {
        ActivityBar,
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
        FontAwesomeIcon,
        UndoRedoStack,
        WorkflowPanel,
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

        const { connectionStore, stepStore, stateStore, commentStore, undoRedoStore } = provideScopedWorkflowStores(id);

        const { undo, redo } = undoRedoStore;
        const { ctrl_z, ctrl_shift_z, meta_z, meta_shift_z } = useMagicKeys();

        const undoKeys = logicOr(ctrl_z, meta_z);
        const redoKeys = logicOr(ctrl_shift_z, meta_shift_z);

        whenever(logicAnd(undoKeys, logicNot(redoKeys)), undo);
        whenever(redoKeys, redo);

        const isCanvas = ref(true);

        const parameters = ref(null);

        function ensureParametersSet() {
            parameters.value = getUntypedWorkflowParameters(steps.value);
        }

        const showInPanel = ref("attributes");

        function showAttributes() {
            ensureParametersSet();
            stateStore.activeNodeId = null;
            showInPanel.value = "attributes";
        }

        const name = ref("Unnamed Workflow");
        const setNameActionHandler = new SetValueActionHandler(
            undoRedoStore,
            (value) => (name.value = value),
            showAttributes,
            "set workflow name"
        );
        /** user set name. queues an undo/redo action */
        function setName(newName) {
            if (name.value !== newName) {
                setNameActionHandler.set(name.value, newName);
            }
        }

        const { report } = storeToRefs(stateStore);

        const license = ref(null);
        const setLicenseHandler = new SetValueActionHandler(
            undoRedoStore,
            (value) => (license.value = value),
            showAttributes,
            "set license"
        );
        /** user set license. queues an undo/redo action */
        function setLicense(newLicense) {
            if (license.value !== newLicense) {
                setLicenseHandler.set(license.value, newLicense);
            }
        }

        const creator = ref(null);
        const setCreatorHandler = new SetValueActionHandler(
            undoRedoStore,
            (value) => (creator.value = value),
            showAttributes,
            "set creator"
        );
        /** user set creator. queues an undo/redo action */
        function setCreator(newCreator) {
            setCreatorHandler.set(creator.value, newCreator);
        }

        const annotation = ref(null);
        const setAnnotationHandler = new SetValueActionHandler(
            undoRedoStore,
            (value) => (annotation.value = value),
            showAttributes,
            "modify annotation"
        );
        /** user set annotation. queues an undo/redo action */
        function setAnnotation(newAnnotation) {
            if (annotation.value !== newAnnotation) {
                setAnnotationHandler.set(annotation.value, newAnnotation);
            }
        }

        const tags = ref([]);

        watch(
            () => props.workflowTags,
            (newTags) => {
                tags.value = [...newTags];
            },
            { immediate: true }
        );

        const setTagsHandler = new SetValueActionHandler(
            undoRedoStore,
            (value) => (tags.value = structuredClone(value)),
            showAttributes,
            "change tags"
        );
        /** user set tags. queues an undo/redo action */
        function setTags(newTags) {
            setTagsHandler.set(tags.value, newTags);
        }

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

        const { hasChanges } = storeToRefs(stateStore);
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
            undoRedoStore.$reset();
            await nextTick();
        }

        onUnmounted(async () => {
            await resetStores();
            emit("update:confirmation", false);
        });

        const stepActions = useStepActions(stepStore, undoRedoStore, stateStore, connectionStore);

        return {
            id,
            name,
            isCanvas,
            parameters,
            ensureParametersSet,
            showInPanel,
            showAttributes,
            setName,
            report,
            license,
            setLicense,
            creator,
            setCreator,
            annotation,
            setAnnotation,
            tags,
            setTags,
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
            stepActions,
            undoRedoStore,
        };
    },
    data() {
        return {
            versions: [],
            labels: {},
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
            saveAsName: null,
            saveAsAnnotation: null,
            showSaveAsModal: false,
            transform: { x: 0, y: 0, k: 1 },
            graphOffset: { left: 0, top: 0, width: 0, height: 0 },
            debounceTimer: null,
            showSaveChangesModal: false,
            navUrl: "",
            workflowEditorActivities,
            specialWorkflowActivities,
        };
    },
    computed: {
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
        updateStep(id, partialStep) {
            this.stepActions.updateStep(id, partialStep);
        },
        onUpdateStepPosition(stepId, position) {
            this.stepActions.setPosition(this.steps[stepId], position);
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
        onChange() {
            this.hasChanges = true;
        },
        onChangePostJobActions(nodeId, postJobActions) {
            const partialStep = { post_job_actions: postJobActions };
            this.stepActions.updateStep(nodeId, partialStep);
        },
        onRemove(nodeId) {
            this.stepActions.removeStep(this.steps[nodeId], this.showAttributes);
        },
        onEditSubworkflow(contentId) {
            const editUrl = `/workflows/edit?workflow_id=${contentId}`;
            this.onNavigate(editUrl);
        },
        async onClone(stepId) {
            const sourceStep = this.steps[parseInt(stepId)];
            this.stepActions.copyStep({
                ...sourceStep,
                id: null,
                uuid: null,
                position: defaultPosition(this.graphOffset, this.transform),
            });
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
                const action = new CopyIntoWorkflowAction(
                    this.id,
                    data,
                    defaultPosition(this.graphOffset, this.transform),
                    true
                );
                this.undoRedoStore.applyAction(action);
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
        async onActivityClicked(activityId) {
            if (activityId === "save-and-exit") {
                if (this.isNewTempWorkflow) {
                    await this.onCreate();
                } else {
                    await this.onSave();
                }

                this.$router.push("/workflows/list");
            }
        },
        onLayout() {
            return import(/* webpackChunkName: "workflowLayout" */ "./modules/layout.ts").then((layout) => {
                layout.autoLayout(this.id, this.steps).then((newSteps) => {
                    newSteps.map((step) => this.stepStore.updateStep(step));
                });
            });
        },
        onAnnotation(nodeId, newAnnotation) {
            this.stepActions.setAnnotation(this.steps[nodeId], newAnnotation);
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
                this.showAttributes();
                return false;
            }
            return true;
        },
        onSetData(stepId, newData) {
            this.lastQueue
                .enqueue(() => getModule(newData, stepId, this.stateStore.setLoadingState))
                .then((data) => {
                    const partialStep = {
                        content_id: data.content_id,
                        inputs: data.inputs,
                        outputs: data.outputs,
                        config_form: data.config_form,
                        tool_state: data.tool_state,
                        tool_version: data.tool_version,
                        errors: data.errors,
                    };
                    this.stepActions.updateStep(stepId, partialStep);
                });
        },
        onLabel(nodeId, newLabel) {
            this.stepActions.setLabel(this.steps[nodeId], newLabel);
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
        },
        onRun() {
            this.onNavigate(`/workflows/run?id=${this.id}`, false, false, true);
        },
        async onNavigate(url, forceSave = false, ignoreChanges = false, appendVersion = false) {
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

            if (appendVersion && this.version !== undefined) {
                url += `&version=${this.version}`;
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
        _insertStep(contentId, name, type) {
            if (!this.isCanvas) {
                this.isCanvas = true;
                return;
            }

            const action = new InsertStepAction(this.stepStore, this.stateStore, {
                contentId,
                name,
                type,
                position: defaultPosition(this.graphOffset, this.transform),
            });

            this.undoRedoStore.applyAction(action);
            const stepData = action.getNewStepData();

            getModule({ name, type, content_id: contentId }, stepData.id, this.stateStore.setLoadingState).then(
                (response) => {
                    const updatedStep = {
                        ...stepData,
                        tool_state: response.tool_state,
                        inputs: response.inputs,
                        outputs: response.outputs,
                        config_form: response.config_form,
                    };

                    this.stepStore.updateStep(updatedStep);
                    action.updateStepData = updatedStep;

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
            this.report.markdown = markdown;
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
        onLicense(license) {
            if (this.license != license) {
                this.hasChanges = true;
                this.setLicense(license);
            }
        },
        onCreator(creator) {
            if (this.creator != creator) {
                this.hasChanges = true;
                this.setCreator(creator);
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

<style scoped lang="scss">
@import "theme/blue.scss";

.editor-top-bar {
    background: $brand-light;
    color: $brand-dark;
    font-size: 1rem;
    font-weight: 700;
    display: flex;
    justify-content: space-between;
    height: 2.5rem;
    padding: 0 1rem;

    & > span {
        overflow: hidden;
        display: flex;
        align-items: center;
    }

    .editor-title {
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }
}

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
