<template>
    <div id="columns" class="d-flex">
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
            ref="activityBar"
            :default-activities="workflowEditorActivities"
            :special-activities="specialWorkflowActivities"
            activity-bar-id="workflow-editor"
            :show-admin="false"
            options-title="Options"
            options-heading="Workflow Options"
            options-tooltip="View additional workflow options"
            options-search-placeholder="Search options"
            initial-activity="workflow-editor-attributes"
            :options-icon="faCog"
            :hide-panel="reportActive"
            @activityClicked="onActivityClicked">
            <template v-slot:side-panel="{ isActiveSideBar }">
                <ToolPanel
                    v-if="isActiveSideBar('workflow-editor-tools')"
                    workflow
                    :module-sections="moduleSections"
                    :data-managers="dataManagers"
                    @onInsertTool="onInsertTool"
                    @onInsertModule="onInsertModule"
                    @onInsertWorkflow="onInsertWorkflow"
                    @onInsertWorkflowSteps="onInsertWorkflowSteps" />
                <InputPanel
                    v-if="isActiveSideBar('workflow-editor-inputs')"
                    :inputs="inputs"
                    @insertModule="onInsertModule" />
                <WorkflowLint
                    v-else-if="isActiveSideBar('workflow-best-practices')"
                    :untyped-parameters="parameters"
                    :annotation="annotation"
                    :creator="creator"
                    :license="license"
                    :steps="steps"
                    :datatypes-mapper="datatypesMapper"
                    @onAttributes="
                        (e) => {
                            showAttributes(e);
                        }
                    "
                    @onHighlight="onHighlight"
                    @onUnhighlight="onUnhighlight"
                    @onRefactor="onAttemptRefactor"
                    @onScrollTo="onScrollTo" />
                <UndoRedoStack v-else-if="isActiveSideBar('workflow-undo-redo')" :store-id="id" />
                <WorkflowPanel
                    v-else-if="isActiveSideBar('workflow-editor-workflows')"
                    :current-workflow-id="id"
                    @insertWorkflow="onInsertWorkflow"
                    @insertWorkflowSteps="onInsertWorkflowSteps"
                    @createWorkflow="createNewWorkflow" />
                <WorkflowAttributes
                    v-else-if="isActiveSideBar('workflow-editor-attributes')"
                    :id="id"
                    :tags="tags"
                    :highlight="highlightAttribute"
                    :parameters="parameters"
                    :annotation="annotation"
                    :name="name"
                    :version="version"
                    :versions="versions"
                    :license="license"
                    :creator="creator"
                    :logo-url="logoUrl"
                    :readme="readme"
                    :help="help"
                    @version="onVersion"
                    @tags="setTags"
                    @license="onLicense"
                    @creator="onCreator"
                    @update:nameCurrent="setName"
                    @update:annotationCurrent="setAnnotation"
                    @update:logoUrlCurrent="setLogoUrl"
                    @update:readmeCurrent="setReadme"
                    @update:helpCurrent="setHelp" />
            </template>
        </ActivityBar>
        <template v-if="reportActive">
            <MarkdownEditor
                ref="markdownEditor"
                :markdown-text="report.markdown"
                mode="report"
                :title="'Workflow Report: ' + name"
                :steps="steps"
                @insert="insertMarkdown"
                @update="onReportUpdate">
                <template v-slot:buttons>
                    <b-button
                        id="workflow-canvas-button"
                        v-b-tooltip.hover.bottom
                        title="Return to Workflow"
                        variant="link"
                        role="button"
                        @click="showAttributes">
                        <FontAwesomeIcon :icon="faTimes" />
                    </b-button>
                </template>
            </MarkdownEditor>
        </template>
        <template v-else>
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
                        <b-button
                            id="workflow-save-button"
                            class="py-1 px-2"
                            variant="link"
                            :disabled="!hasChanges"
                            :title="saveWorkflowTitle"
                            @click="saveOrCreate">
                            <FontAwesomeIcon :icon="faSave" />
                        </b-button>
                    </b-button-group>
                </div>
                <WorkflowGraph
                    v-if="!datatypesMapperLoading"
                    ref="workflowGraph"
                    :steps="steps"
                    :datatypes-mapper="datatypesMapper"
                    :highlight-id="highlightId"
                    :scroll-to-id="scrollToId"
                    :initial-position="{ x: 50, y: 50 }"
                    @scrollTo="scrollToId = null"
                    @transform="(value) => (transform = value)"
                    @graph-offset="(value) => (graphOffset = value)"
                    @onClone="onClone"
                    @onCreate="onInsertTool"
                    @onChange="onChange"
                    @onRemove="onRemove"
                    @onUpdateStepPosition="onUpdateStepPosition">
                    <NodeInspector
                        v-if="activeStep"
                        :step="activeStep"
                        :datatypes="datatypes"
                        @postJobActionsChanged="onChangePostJobActions"
                        @annotationChanged="onAnnotation"
                        @labelChanged="onLabel"
                        @dataChanged="onSetData"
                        @stepUpdated="updateStep"
                        @editSubworkflow="onEditSubworkflow"
                        @attemptRefactor="onAttemptRefactor"
                        @close="activeNodeId = null"></NodeInspector>
                </WorkflowGraph>
            </div>
        </template>
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArrowLeft, faArrowRight, faCog, faHistory, faSave, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { until, whenever } from "@vueuse/core";
import { logicAnd, logicNot, logicOr } from "@vueuse/math";
import { Toast } from "composables/toast";
import { storeToRefs } from "pinia";
import Vue, { computed, nextTick, onUnmounted, ref, unref, watch } from "vue";

import { getUntypedWorkflowParameters } from "@/components/Workflow/Editor/modules/parameters";
import { ConfirmDialog, useConfirmDialog } from "@/composables/confirmDialog";
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
import { useActivityLogic, useSpecialWorkflowActivities, workflowEditorActivities } from "./modules/activities";
import { getWorkflowInputs } from "./modules/inputs";
import { fromSimple } from "./modules/model";
import { getModule, getVersions, loadWorkflow, saveWorkflow } from "./modules/services";
import { getStateUpgradeMessages } from "./modules/utilities";
import reportDefault from "./reportDefault";

import WorkflowLint from "./Lint.vue";
import MessagesModal from "./MessagesModal.vue";
import NodeInspector from "./NodeInspector.vue";
import RefactorConfirmationModal from "./RefactorConfirmationModal.vue";
import SaveChangesModal from "./SaveChangesModal.vue";
import StateUpgradeModal from "./StateUpgradeModal.vue";
import WorkflowAttributes from "./WorkflowAttributes.vue";
import WorkflowGraph from "./WorkflowGraph.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import MarkdownEditor from "@/components/Markdown/MarkdownEditor.vue";
import InputPanel from "@/components/Panels/InputPanel.vue";
import ToolPanel from "@/components/Panels/ToolPanel.vue";
import WorkflowPanel from "@/components/Panels/WorkflowPanel.vue";
import UndoRedoStack from "@/components/UndoRedo/UndoRedoStack.vue";

library.add(faArrowLeft, faArrowRight, faHistory);

export default {
    components: {
        ActivityBar,
        MarkdownEditor,
        SaveChangesModal,
        StateUpgradeModal,
        ToolPanel,
        WorkflowAttributes,
        WorkflowLint,
        RefactorConfirmationModal,
        MessagesModal,
        WorkflowGraph,
        FontAwesomeIcon,
        UndoRedoStack,
        WorkflowPanel,
        NodeInspector,
        InputPanel,
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

        const activityBar = ref(null);
        const workflowGraph = ref(null);
        const reportActive = computed(() => activityBar.value?.isActiveSideBar("workflow-editor-report"));

        const parameters = ref(null);

        function ensureParametersSet() {
            parameters.value = getUntypedWorkflowParameters(steps.value);
        }

        function showAttributes(args) {
            ensureParametersSet();
            stateStore.activeNodeId = null;
            activityBar.value?.setActiveSideBar("workflow-editor-attributes");
            if (args?.highlight) {
                this.highlightAttribute = args.highlight;
            }
        }

        const name = ref("未命名工作流");
        const setNameActionHandler = new SetValueActionHandler(
            undoRedoStore,
            (value) => (name.value = value),
            showAttributes,
            "设置工作流名称"
        );
        /** 用户设置名称，排队撤销/重做操作 */
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
            "设置许可协议"
        );
        /** 用户设置许可协议，排队撤销/重做操作 */
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
            "设置创建者"
        );
        /** 用户设置创建者，排队撤销/重做操作 */
        function setCreator(newCreator) {
            setCreatorHandler.set(creator.value, newCreator);
        }

        const annotation = ref(null);
        const setAnnotationHandler = new SetValueActionHandler(
            undoRedoStore,
            (value) => (annotation.value = value),
            showAttributes,
            "修改简短描述"
        );
        /** 用户设置简短描述，排队撤销/重做操作 */
        function setAnnotation(newAnnotation) {
            if (annotation.value !== newAnnotation) {
                setAnnotationHandler.set(annotation.value, newAnnotation);
            }
        }

        const readme = ref(null);
        const setReadmeHandler = new SetValueActionHandler(
            undoRedoStore,
            (value) => (readme.value = value),
            showAttributes,
            "修改自述文件"
        );
        function setReadme(newReadme) {
            if (readme.value !== newReadme) {
                setReadmeHandler.set(readme.value, newReadme);
            }
        }

        const help = ref(null);
        const setHelpHandler = new SetValueActionHandler(
            undoRedoStore,
            (value) => (help.value = value),
            showAttributes,
            "修改帮助信息"
        );
        function setHelp(newHelp) {
            if (help.value !== newHelp) {
                setHelpHandler.set(help.value, newHelp);
            }
        }

        const logoUrl = ref(null);
        const setLogoUrlHandler = new SetValueActionHandler(
            undoRedoStore,
            (value) => (logoUrl.value = value),
            showAttributes,
            "修改Logo地址"
        );
        function setLogoUrl(newLogoUrl) {
            if (logoUrl.value !== newLogoUrl) {
                setLogoUrlHandler.set(logoUrl.value, newLogoUrl);
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
            "修改标签"
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

        const markdownEditor = ref(null);
        function insertMarkdown(markdown) {
            markdownEditor.value?.insertMarkdown(markdown);
        }

        const isNewTempWorkflow = computed(() => !props.workflowId);

        const { specialWorkflowActivities } = useSpecialWorkflowActivities(
            computed(() => ({
                hasInvalidConnections: hasInvalidConnections.value,
            }))
        );

        const saveWorkflowTitle = computed(() =>
            hasInvalidConnections.value
                ? "工作流存在无效连接，请检查并移除无效连接"
                : "保存工作流"
        );

        useActivityLogic(
            computed(() => ({
                activityBarId: "workflow-editor",
                isNewTempWorkflow: isNewTempWorkflow.value,
            }))
        );

        const { confirm } = useConfirmDialog();
        const inputs = getWorkflowInputs();

        return {
            id,
            name,
            parameters,
            workflowGraph,
            ensureParametersSet,
            showAttributes,
            setName,
            report,
            license,
            setLicense,
            creator,
            setCreator,
            annotation,
            setAnnotation,
            readme,
            setReadme,
            help,
            setHelp,
            logoUrl,
            setLogoUrl,
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
            activityBar,
            reportActive,
            markdownEditor,
            insertMarkdown,
            specialWorkflowActivities,
            isNewTempWorkflow,
            saveWorkflowTitle,
            confirm,
            inputs,
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
            highlightAttribute: null,
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
            faTimes,
            faCog,
            faSave,
        };
    },
    computed: {
        activeNodeType() {
            return this.activeStep?.type;
        },
        hasActiveNodeDefault() {
            return this.activeStep && this.activeStep?.type != "tool";
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
        readme(newReadme, oldReadme) {
            if (newReadme != oldReadme) {
                this.hasChanges = true;
            }
        },
        help(newHelp, oldHelp) {
            if (newHelp != oldHelp) {
                this.hasChanges = true;
            }
        },
        logoUrl(newLogoUrl, oldLogoUrl) {
            if (newLogoUrl != oldLogoUrl) {
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
                    "您的工作流已进行更改，必须保存这些更改后才能执行请求的操作。是否保存更改并继续？"
                );
                if (r == false) {
                    return;
                }
                this.onWorkflowMessage("正在保存工作流...", "progress");
                return saveWorkflow(this)
                    .then((data) => {
                        this.refactorActions = actions;
                    })
                    .catch((response) => {
                        this.onWorkflowError("保存工作流失败，无法应用请求的更改...", response, {
                            确定: () => {
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
            this.stepActions.removeStep(this.steps[nodeId]);
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
        async onInsertModule(module_id, module_name, state) {
            this._insertStep(module_name, module_name, module_id, state);
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
            if (stepCount < 10) {
                this.copyIntoWorkflow(workflowId);
            } else {
                const confirmed = await ConfirmDialog.confirm(
                    `警告：这将把 ${stepCount} 个新步骤添加到当前工作流中。您可能想考虑使用子工作流。`
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
                const message = `已创建新工作流 '${name}'，包含 ${number_of_steps} 个步骤。`;
                this.hasChanges = false;
                await this.routeToWorkflow(id);
                Toast.success(message);
            } catch (e) {
                const errorHeading = `将工作流保存为 '${rename_name}' 失败`;
                this.onWorkflowError(errorHeading, errorMessageAsString(e) || "请联系管理员。", {
                    确定: () => {
                        this.hideModal();
                    },
                });
            }
        },
        onSaveAs() {
            this.showSaveAsModal = true;
        },
        async createNewWorkflow() {
            await this.saveOrCreate();
            this.$router.push("/workflows/edit");
        },
        async saveOrCreate() {
            if (this.hasInvalidConnections) {
                const confirmed = await this.confirm(
                    `工作流存在无效的连接。您可以保存工作流，但它可能无法正常运行。`,
                    {
                        id: "save-workflow-confirmation",
                        okTitle: "保存工作流",
                    }
                );

                if (!confirmed) {
                    return;
                }
            }

            if (this.isNewTempWorkflow) {
                await this.onCreate();
            } else {
                await this.onSave();
            }
        },
        async onActivityClicked(activityId) {
            if (activityId === "save-and-exit") {
                await this.saveOrCreate();
                this.$router.push("/workflows/list");
            }

            if (activityId === "exit") {
                this.$router.push("/workflows/list");
            }

            if (activityId === "workflow-download") {
                this.onDownload();
            }

            if (activityId === "workflow-upgrade") {
                this.onUpgrade();
            }

            if (activityId === "workflow-run") {
                this.onRun();
            }

            if (activityId === "save-workflow") {
                await this.saveOrCreate();
            }

            if (activityId === "save-workflow-as") {
                this.onSaveAs();
            }

            if (activityId === "workflow-create") {
                this.createNewWorkflow();
            }
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
                const message = `已创建新工作流 '${name}'，包含 ${number_of_steps} 个步骤。`;
                this.hasChanges = false;
                this.$emit("skipNextReload");
                await this.routeToWorkflow(id);
                Toast.success(message);
            } catch (e) {
                this.onWorkflowError(
                    "创建工作流失败",
                    errorMessageAsString(e) || "请联系管理员。",
                    {
                        确定: () => {
                            this.hideModal();
                        },
                    }
                );
            }
        },
        nameValidate() {
            if (!this.name) {
                Toast.error("请为你的工作流提供名称.");
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
            !hideProgress && this.onWorkflowMessage("正在保存工作流...", "progress");
            return saveWorkflow(this)
                .then((data) => {
                    getVersions(this.id).then((versions) => {
                        this.versions = versions;
                        this.hideModal();
                    });
                })
                .catch((response) => {
                    this.onWorkflowError("保存工作流失败...", response, {
                        确定: () => {
                            this.hideModal();
                        },
                    });
                });
        },
        onVersion(version) {
            if (version != this.version) {
                if (this.hasChanges) {
                    const r = window.confirm(
                        "工作流程中未保存的更改将丢失。继续？"
                    );
                    if (r == false) {
                        return;
                    }
                }
                this.version = version;
                this._loadCurrent(this.id, version);
            }
        },
        async _insertStep(contentId, name, type, state) {
            const action = new InsertStepAction(this.stepStore, this.stateStore, {
                contentId,
                name,
                type,
                position: defaultPosition(this.graphOffset, this.transform),
            });

            this.undoRedoStore.applyAction(action);
            const stepData = action.getNewStepData();

            const response = await getModule(
                { name, type, content_id: contentId, tool_state: state },
                stepData.id,
                this.stateStore.setLoadingState
            );

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
        },
        async _loadEditorData(data) {
            if (data.name !== undefined) {
                this.name = data.name;
            }
            if (data.annotation !== undefined) {
                this.annotation = data.annotation;
            }
            if (data.readme !== undefined) {
                this.readme = data.readme;
            }
            if (data.help !== undefined) {
                this.help = data.help;
            }
            if (data.logo_url !== undefined) {
                this.logoUrl = data.logo_url;
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
                this.onWorkflowMessage("加载工作流...", "progress");

                try {
                    const data = await this.lastQueue.enqueue(loadWorkflow, { id, version });
                    await fromSimple(id, data);
                    await this._loadEditorData(data);
                } catch (e) {
                    this.onWorkflowError("加载工作流失败...", e);
                }

                await until(() => this.datatypesMapperLoading).toBe(false);
                await nextTick();

                this.workflowGraph.fitWorkflow();
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
