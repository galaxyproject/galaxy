<script setup lang="ts">
import {
    faCog,
    faKey,
    faMagic,
    faRedo,
    faSave,
    faSitemap,
    faTimes,
    faUndo,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { until, whenever } from "@vueuse/core";
import { logicAnd, logicNot, logicOr } from "@vueuse/math";
import { BDropdown, BDropdownDivider, BDropdownItem, BDropdownText, BFormTextarea } from "bootstrap-vue";
import type { ZoomTransform } from "d3-zoom";
import isEqual from "lodash.isequal";
import { storeToRefs } from "pinia";
import { computed, nextTick, onUnmounted, ref, unref, watch } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { generateAIReport as generateAIReportFetch } from "@/api/chat";
import type { Creator, RefactorRequestAction } from "@/api/workflows";
import { InsertStepAction, useStepActions } from "@/components/Workflow/Editor/Actions/stepActions";
import { CopyIntoWorkflowAction, SetValueActionHandler } from "@/components/Workflow/Editor/Actions/workflowActions";
import { defaultPosition } from "@/components/Workflow/Editor/composables/useDefaultStepPosition";
import { useSpecialWorkflowActivities, useWorkflowActivities } from "@/components/Workflow/Editor/modules/activities";
import { fromSimple, type Workflow } from "@/components/Workflow/Editor/modules/model";
import { getUntypedWorkflowParameters, type UntypedParameters } from "@/components/Workflow/Editor/modules/parameters";
import { getModule, getVersions, saveWorkflow } from "@/components/Workflow/Editor/modules/services";
import { getStateUpgradeMessages, type UpgradeMessage } from "@/components/Workflow/Editor/modules/utilities";
import reportDefault from "@/components/Workflow/Editor/reportDefault";
import { Services } from "@/components/Workflow/services";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { useToast } from "@/composables/toast";
import { useMagicKeys } from "@/composables/useMagicKeys";
import { useUid } from "@/composables/utils/uid";
import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import { getAppRoot } from "@/onload/loadConfig";
import { useScopePointerStore } from "@/stores/scopePointerStore";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";
import type { SearchData } from "@/stores/workflowSearchStore";
import type { NewStep, PostJobActions, Step } from "@/stores/workflowStepStore";
import type { WorkflowTransform } from "@/utils/geometry";
import { LastQueue } from "@/utils/lastQueue";
import { errorMessageAsString } from "@/utils/simple-error";
import { textify } from "@/utils/utils";

import { getWorkflowFull } from "../workflows.services";
import { type BoundingBoxBounds, useWorkflowBoundingBox } from "./composables/workflowBoundingBox";
import { getWorkflowInputs, type WorkflowInput } from "./modules/inputs";
import { fromSteps } from "./modules/labels";
import { useLintData } from "./modules/useLinting";

import ReadmeEditor from "./ReadmeEditor.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import GForm from "@/components/BaseComponents/Form/GForm.vue";
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GFormLabel from "@/components/BaseComponents/Form/GFormLabel.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import MarkdownEditor from "@/components/Markdown/MarkdownEditor.vue";
import InputPanel from "@/components/Panels/InputPanel.vue";
import SearchPanel from "@/components/Panels/SearchPanel.vue";
import ToolPanel from "@/components/Panels/ToolPanel.vue";
import UserToolPanel from "@/components/Panels/UserToolPanel.vue";
import WorkflowPanel from "@/components/Panels/WorkflowPanel.vue";
import UndoRedoStack from "@/components/UndoRedo/UndoRedoStack.vue";
import WorkflowLint from "@/components/Workflow/Editor/Lint.vue";
import NodeInspector from "@/components/Workflow/Editor/NodeInspector.vue";
import RefactorConfirmationModal from "@/components/Workflow/Editor/RefactorConfirmationModal.vue";
import SaveChangesModal from "@/components/Workflow/Editor/SaveChangesModal.vue";
import StateUpgradeModal from "@/components/Workflow/Editor/StateUpgradeModal.vue";
import WorkflowAttributes from "@/components/Workflow/Editor/WorkflowAttributes.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";

interface Props {
    workflowId?: string;
    initialVersion?: number;
    workflowTags?: string[];
}

const props = withDefaults(defineProps<Props>(), {
    workflowId: undefined,
    initialVersion: undefined,
    workflowTags: () => [],
});
const emit = defineEmits<{
    (e: "skipNextReload"): void;
    (e: "update:confirmation", value: boolean): void;
    (e: "forceReload"): void;
}>();

const route = useRoute();
const router = useRouter();

const Toast = useToast();

const { confirm } = useConfirmDialog();

const inputs = getWorkflowInputs();

const services = new Services();
const lastQueue = new LastQueue();

const { datatypes, datatypesMapper, datatypesMapperLoading } = useDatatypesMapper();

const uid = unref(useUid("workflow-editor-"));

// Central `id` ref and stores setup
const id = ref(props.workflowId || uid);

const { connectionStore, stepStore, stateStore, commentStore, undoRedoStore } = provideScopedWorkflowStores(id);

const { captureTransformAndBounds, calculateAdjustedTransform } = useWorkflowBoundingBox(id.value);

// Undo/Redo keyboard shortcuts and stack
const { undo, redo } = undoRedoStore;
const { undoStackLength } = storeToRefs(undoRedoStore);
const { ctrl_z, ctrl_shift_z, meta_z, meta_shift_z } = useMagicKeys();

const undoKeys = logicOr(ctrl_z, meta_z);
const redoKeys = logicOr(ctrl_shift_z, meta_shift_z);

/** Tracks when the workflow is being fetched or an operation is ongoing */
const loadingWorkflow = ref(false);

whenever(logicAnd(undoKeys, logicNot(redoKeys)), () => !loadingWorkflow.value && undo());
whenever(redoKeys, () => !loadingWorkflow.value && redo());

const workflowGraph = ref<InstanceType<typeof WorkflowGraph> | null>(null);

// Activity bar and sidebar state
const activityBar = ref<InstanceType<typeof ActivityBar> | null>(null);
function isActiveSideBar(activityBarId: string) {
    return activityBar.value?.isActiveSideBar(activityBarId);
}
const reportActive = computed(() => isActiveSideBar("workflow-editor-report"));

const parameters = ref<UntypedParameters>();

function ensureParametersSet() {
    parameters.value = getUntypedWorkflowParameters(steps.value);
}

function showAttributes(args?: any) {
    ensureParametersSet();
    stateStore.activeNodeId = null;
    activityBar.value?.setActiveSideBar("workflow-editor-attributes");

    if (args?.highlight) {
        highlightAttribute.value = args.highlight;
    }
}

// Workflow attributes refs and handlers -------------------------------------

/** Current version of the workflow. `null` if the workflow is unversioned. */
const version = ref<number | null>(props.initialVersion !== undefined ? props.initialVersion : null);

/** All versions of the workflow, fetched from the server. */
const versions = ref<{ version: number; update_time: string; steps: number }[]>([]);

/** Attribute element that is highlighted in the workflow attributes panel. */
const highlightAttribute = ref<string | undefined>();

const name = ref("Unnamed Workflow");
const setNameActionHandler = new SetValueActionHandler(
    undoRedoStore,
    (value) => (name.value = value as string),
    showAttributes,
    "set workflow name",
);
/** user set name. queues an undo/redo action */
function setName(newName: string) {
    if (name.value !== newName) {
        setNameActionHandler.set(name.value, newName);
    }
}

const { report } = storeToRefs(stateStore);

// TODO: Explore setting several of these attributes to what is in the schema
// e.g.: `StoredWorkflowDetailed` has `license?: string | null;`
const license = ref("");
const setLicenseHandler = new SetValueActionHandler(
    undoRedoStore,
    (value) => (license.value = value as string),
    showAttributes,
    "set license",
    "license",
);
/** user set license. queues an undo/redo action */
function setLicense(newLicense: string) {
    if (license.value !== newLicense) {
        setLicenseHandler.set(license.value, newLicense);
    }
}

const creator = ref<Creator[] | null>(null);
const setCreatorHandler = new SetValueActionHandler(
    undoRedoStore,
    (value) => (creator.value = value as Creator[] | null),
    showAttributes,
    "set creator",
    "creator",
);
/** user set creator. queues an undo/redo action */
function setCreator(newCreator?: Creator[] | null) {
    setCreatorHandler.set(creator.value, newCreator);
}

const doi = ref<string[] | null>(null);
const setDoiHandler = new SetValueActionHandler(
    undoRedoStore,
    (value) => (doi.value = value as string[] | null),
    showAttributes,
    "set DOI",
    "DOI",
);
function setDoi(newDoi: string[] | null) {
    setDoiHandler.set(doi.value, newDoi);
}

const annotation = ref<string>("");
const setAnnotationHandler = new SetValueActionHandler(
    undoRedoStore,
    (value) => (annotation.value = value as string),
    showAttributes,
    "modify short description",
    "annotation",
);
/** user set annotation. queues an undo/redo action */
function setAnnotation(newAnnotation: string) {
    if (annotation.value !== newAnnotation) {
        setAnnotationHandler.set(annotation.value, newAnnotation);
    }
}

const readme = ref<string>("");
const readmeActive = ref(false);
const setReadmeHandler = new SetValueActionHandler(
    undoRedoStore,
    (value) => (readme.value = value as string),
    () => {
        showAttributes();
        readmeActive.value = true;
    },
    "modify readme",
    "readme",
);
function setReadme(newReadme: string) {
    if (readme.value !== newReadme) {
        setReadmeHandler.set(readme.value, newReadme);
    }
}
// The readme editor should only be active while the attributes activity is active,
// closing it as soon as the user navigates to any other activity. `workflow-undo-redo`
// is the one exception, since it can be toggled open alongside the attributes panel.
watch(
    () => isActiveSideBar("workflow-editor-attributes") || isActiveSideBar("workflow-undo-redo"),
    (stillEligible) => {
        if (!stillEligible) {
            readmeActive.value = false;
        }
    },
);

const help = ref<string>("");
const setHelpHandler = new SetValueActionHandler(
    undoRedoStore,
    (value) => (help.value = value as string),
    showAttributes,
    "modify help",
);
function setHelp(newHelp: string) {
    if (help.value !== newHelp) {
        setHelpHandler.set(help.value, newHelp);
    }
}

const logoUrl = ref<string>("");
const setLogoUrlHandler = new SetValueActionHandler(
    undoRedoStore,
    (value) => (logoUrl.value = value as string),
    showAttributes,
    "modify logo url",
);
function setLogoUrl(newLogoUrl: string) {
    if (logoUrl.value !== newLogoUrl) {
        setLogoUrlHandler.set(logoUrl.value, newLogoUrl);
    }
}

const tags = ref<string[]>(props.workflowTags || []);
/** Updates local `tags` state. **Does not** queue an undo/redo action as the tags are set
 * instantly in `WorkflowAttributes` via the backend on the workflow without
 * creating a new version, meaning we don't need to queue an undo/redo action for them.
 */
function setTags(newTags: string[]) {
    tags.value = structuredClone(newTags);
}

// ---------------------------------------------------------------------------

// For the State Upgrade modal
const stateMessages = ref<UpgradeMessage[]>([]);
const insertedStateMessages = ref<UpgradeMessage[]>([]);

/** Refactor actions that are queued up to be executed on the workflow. */
const refactorActions = ref<RefactorRequestAction[]>([]);

// For the error modal
const errorMessageTitle = ref<string | null>(null);
const errorMessageBody = ref<string | null>(null);

// For the Save As modal
const saveAsName = ref<string | null>(null);
const saveAsAnnotation = ref<string | null>(null);
const showSaveAsModal = ref(false);

// For the Save Changes modal
const showSaveChangesModal = ref(false);
const saveChangesAppendVersion = ref(false);
const navUrl = ref("");

const rightPanelElement = ref<HTMLElement | null>(null);
function scrollToTop() {
    rightPanelElement.value?.scrollTo({
        top: 0,
        behavior: "instant",
    });
}
// Scroll to top when the active node changes
watch(
    () => stateStore.activeNodeId,
    () => {
        scrollToTop();
    },
);

// Comments, Steps and State stores
const { comments } = storeToRefs(commentStore);
const { steps, duplicateLabels } = storeToRefs(stepStore);
const { activeNodeId, hasChanges } = storeToRefs(stateStore);
const activeStep = computed(() => {
    if (activeNodeId.value !== null) {
        return stepStore.getStep(activeNodeId.value);
    }
    return null;
});
const hasInvalidConnections = computed(() => Object.keys(connectionStore.invalidConnections).length > 0);
const hasDuplicateOutputs = computed(() => duplicateLabels.value.size > 0);

// Error handling and text for the workflow editor
const hasErrors = computed(() => hasInvalidConnections.value || hasDuplicateOutputs.value);

const errorText = computed(() => {
    const texts = [];

    if (hasInvalidConnections.value) {
        texts.push("invalid connections");
    }

    if (hasDuplicateOutputs.value) {
        texts.push("duplicate output labels");
    }

    return `Workflow has ${textify(texts, "and")}`;
});

/** Is true on initial load of when this component is mounted, and false after that.
 * Used to avoid setting `hasChanges` on initial load. */
const initialLoading = ref(true);

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

/** Workflow data object that is used for saving and creating workflows.
 * It is a computed property that returns an object with the current values of the workflow properties. */
const workflowData = computed<Workflow>(() => ({
    id: id.value,
    name: name.value,
    annotation: annotation.value,
    license: license.value,
    creator: creator.value,
    version: version.value ?? undefined,
    report: report.value,
    steps: steps.value,
    comments: comments.value,
    tags: tags.value,
    logo_url: logoUrl.value,
    readme: readme.value,
    help: help.value,
    doi: doi.value || undefined,
}));

/** Is true when we are on a fresh workflow editor with no ID yet (uncreated workflow) */
const isNewTempWorkflow = computed(() => !props.workflowId);

/** Boolean flag to toggle the visibility of the credentials dropdown menu in the top bar */
const showCredentialsDropdown = ref(false);

const unprivilegedToolStore = useUnprivilegedToolStore();
const { canUseUnprivilegedTools } = storeToRefs(unprivilegedToolStore);

/** Workflow activities specific to the workflow editor activity bar */
const workflowActivities = useWorkflowActivities(
    "workflow-editor",
    isNewTempWorkflow,
    hasChanges,
    undoStackLength,
    canUseUnprivilegedTools,
);

/** Lint/Best Practices panel data */
const lintData = useLintData(id, steps, datatypesMapper, annotation, readme, license, creator);

/** Activities locked at the bottom of the workflow editor activity bar */
const { bestPracticesActivity, exitWorkflowActivity, runWorkflowActivity } = useSpecialWorkflowActivities(
    computed(() => ({
        lintData: lintData,
    })),
);

/** Markdown Editor labels */
const getLabels = computed(() => fromSteps(steps.value));

/** Tooltip to show on the Save button in the top bar */
const saveWorkflowTitle = computed(() =>
    hasInvalidConnections.value
        ? `${errorText.value}, review and remove workflow errors.`
        : hasChanges.value
          ? "Save Workflow"
          : "No changes to save.",
);

const credentialSteps = computed(() => {
    return Object.values(steps.value).filter(
        (step) => step.type === "tool" && step.config_form?.credentials?.length > 0,
    );
});

const scrollToId = ref<number | null>(null);

function onHighlightRegion(result: SearchData) {
    stateStore.pendingHighlight = { bounds: result.bounds };
}

function onScrollTo(stepId: number) {
    scrollToId.value = stepId;
}

function onToolClick(toolId: number) {
    stateStore.activeNodeId = toolId;
    onScrollTo(toolId);
}

// For keeping track of the workflow graph transform and bounds, so we can adjust for coordinate shifts
const transform = ref<ZoomTransform>({ x: 0, y: 0, k: 1 } as ZoomTransform);
const graphOffset = ref({
    left: 0,
    top: 0,
    width: 0,
    height: 0,
    bottom: 0,
    right: 0,
    x: 0,
    y: 0,
    update: () => {},
});

// Several watchers ----------------------------------------------------------

watch(
    () => id.value,
    (newId, oldId) => {
        if (oldId) {
            loadCurrent(newId, undefined, true);
        }
    },
);

watch(
    () => props.workflowTags,
    (newTags) => {
        tags.value = [...newTags];
    },
    { immediate: true },
);

// `SetValueActionHandler`/`LazySetValueAction` only queue undo/redo actions and write the
// value back via `setValueHandler` — they never touch `hasChanges`. These watchers are the
// only thing that marks the workflow dirty when these attributes change, so they're required.
watch(
    () => annotation.value,
    (newAnnotation, oldAnnotation) => {
        if (newAnnotation != oldAnnotation) {
            hasChanges.value = true;
        }
    },
);

watch(
    () => name.value,
    (newName, oldName) => {
        if (newName != oldName) {
            hasChanges.value = true;
        }
    },
);

watch(
    () => readme.value,
    (newReadme, oldReadme) => {
        if (newReadme != oldReadme) {
            hasChanges.value = true;
        }
    },
);

watch(
    () => help.value,
    (newHelp, oldHelp) => {
        if (newHelp != oldHelp) {
            hasChanges.value = true;
        }
    },
);

watch(
    () => logoUrl.value,
    (newLogoUrl, oldLogoUrl) => {
        if (newLogoUrl != oldLogoUrl) {
            hasChanges.value = true;
        }
    },
);

watch(
    () => hasChanges.value,
    (newHasChanges) => {
        emit("update:confirmation", newHasChanges);
    },
);

watch(
    () => props.initialVersion,
    (newVal, oldVal) => {
        if (newVal != oldVal && oldVal === undefined) {
            version.value = newVal ?? null;
        }
    },
);

// ---------------------------------------------------------------------------
// General functions for workflow editor actions

/**
 * Used to block certain actions while the workflow is loading, and show a warning toast to the user.
 * @param [action="making changes"] Text followed by the prefix in the warning toast
 * @returns `true` if the workflow is currently loading, and a warning toast is shown to the user.
 */
function blockedWhileLoading(action = "making changes") {
    if (loadingWorkflow.value) {
        Toast.warning(`Please wait for the workflow to finish loading before ${action}.`);
        return true;
    }
    return false;
}

function updateStep(stepId: number, partialStep: Partial<Step>) {
    stepActions.updateStep(stepId, partialStep);
}

function onUpdateStepPosition(stepId: string, position: NonNullable<Step["position"]>) {
    const tmpStep = steps.value[stepId];
    if (tmpStep) {
        stepActions.setPosition(tmpStep, position);
    }
}

async function onAttemptRefactor(actions: any[]) {
    if (blockedWhileLoading()) {
        return;
    }
    if (hasChanges.value) {
        const confirmed = await confirm(
            "You've made changes to your workflow that need to be saved before attempting the requested action. Save those changes and continue?",
        );

        if (!confirmed) {
            return;
        }

        if (await onSave()) {
            refactorActions.value = actions;
        }
    } else {
        refactorActions.value = actions;
    }
}

function onWorkflowError(title: string, body: string) {
    errorMessageTitle.value = title;
    errorMessageBody.value = body;
}

function hideErrorModal() {
    errorMessageTitle.value = null;
    errorMessageBody.value = null;
}

async function onRefactor(response: { workflow: any }) {
    // Store transform and bounds before resetting to adjust for coordinate shifts
    const { transform: transformBefore, bounds: boundsBefore } = captureTransformAndBounds(transform.value);

    await resetStores();
    await fromSimple(id.value, response.workflow);
    await loadEditorData(response.workflow);

    // Adjust for coordinate shifts so nodes appear in the same position
    // and stateStore.position is synced with the d3 transform
    adjustForCoordinateShift(transformBefore, boundsBefore);
}

function onChangePostJobActions(nodeId: number, postJobActions: PostJobActions) {
    const partialStep = { post_job_actions: postJobActions };
    stepActions.updateStep(nodeId, partialStep);
}

function onRemove(nodeId: string) {
    if (blockedWhileLoading("removing a step")) {
        return;
    }

    const tmpStep = steps.value[nodeId];
    if (tmpStep) {
        stepActions.removeStep(tmpStep);
    }
}

function onEditSubWorkflow(contentId: string) {
    onNavigate(`/workflows/edit?workflow_id=${contentId}`);
}

async function onClone(stepId: string) {
    if (blockedWhileLoading("cloning a step")) {
        return;
    }

    const sourceStep = steps.value[parseInt(stepId)];
    if (sourceStep) {
        const newStep = {
            ...sourceStep,
            position: defaultPosition(graphOffset.value, transform.value),
        };

        stepActions.copyStep(newStep);
    }
}

function onInsertTool(toolId: string, toolName: string, toolUuid?: string) {
    if (blockedWhileLoading("inserting a tool")) {
        return;
    }
    insertStep(toolId, toolName, "tool", undefined, toolUuid);
}

function onInsertModule(
    moduleId: WorkflowInput["moduleId"],
    moduleName: string,
    state: WorkflowInput["stateOverwrites"],
) {
    if (blockedWhileLoading("inserting a step")) {
        return;
    }
    insertStep(moduleName, moduleName, moduleId, state);
}

async function onInsertWorkflow(workflowId: string, workflowName: string) {
    if (blockedWhileLoading("inserting a subworkflow")) {
        return;
    }
    insertStep(workflowId, workflowName, "subworkflow");
}

async function copyIntoWorkflow(workflowId: string) {
    // Load workflow definition
    loadingWorkflow.value = true;
    try {
        const data = await getWorkflowFull(workflowId);
        const action = new CopyIntoWorkflowAction(id.value, data, defaultPosition(graphOffset.value, transform.value));
        undoRedoStore.applyAction(action);
        // Determine if any parameters were 'upgraded' and provide message
        const insertedStateMessagesGotten = getStateUpgradeMessages(data);
        insertedStateMessages.value = insertedStateMessagesGotten;
    } finally {
        loadingWorkflow.value = false;
    }
}

async function onInsertWorkflowSteps(workflowId: string, stepCount?: number) {
    if (blockedWhileLoading("inserting steps")) {
        return;
    }

    if (stepCount !== undefined && stepCount < 10) {
        await copyIntoWorkflow(workflowId);
    } else {
        const confirmed = await confirm(
            `Warning this will add ${stepCount} new steps into your current workflow.  You may want to consider using a subworkflow instead.`,
        );

        if (confirmed) {
            await copyIntoWorkflow(workflowId);
        }
    }
}

function onDownload() {
    window.location.href = `${getAppRoot()}api/workflows/${id.value}/download?format=json-download`;
}

async function doSaveAs() {
    if (!saveAsName.value && !nameValidate()) {
        return;
    }

    loadingWorkflow.value = true;

    const renameName = saveAsName.value ?? `SavedAs_${name.value}`;
    const renameAnnotation = saveAsAnnotation.value ?? "";

    try {
        const newSaveAsWf = { ...workflowData.value, name: renameName, annotation: renameAnnotation };
        const { id: newId, name: newName, number_of_steps } = await services.createWorkflow(newSaveAsWf);

        hasChanges.value = false;

        await routeToWorkflow(newId);

        Toast.success(`Created new workflow '${newName}' with ${number_of_steps} steps.`);
    } catch (e) {
        const errorHeading = `Saving workflow as '${renameName}' failed`;
        onWorkflowError(errorHeading, errorMessageAsString(e, "Please contact an administrator."));
    } finally {
        loadingWorkflow.value = false;
        resetSaveAs();
    }
}

function onSaveAs() {
    if (blockedWhileLoading("saving the workflow")) {
        return;
    }
    showSaveAsModal.value = true;
}

function resetSaveAs() {
    saveAsName.value = null;
    saveAsAnnotation.value = null;
}

async function createNewWorkflow() {
    await onNavigate("/workflows/edit");
}

async function saveOrCreate() {
    if (blockedWhileLoading("saving the workflow")) {
        return;
    }
    if (hasErrors.value) {
        const confirmed = await confirm(
            `${errorText.value}. You can save the workflow, but it may not run correctly.`,
            {
                title: "Workflow has errors",
                okText: "Save Workflow",
            },
        );

        if (!confirmed) {
            return;
        }
    }

    if (isNewTempWorkflow.value) {
        await onCreate();
    } else {
        await onSave();
    }
}

async function onActivityClicked(activityId: string) {
    if (activityId === "exit") {
        await onNavigate("/workflows/list");
    } else if (activityId === "workflow-download") {
        onDownload();
    } else if (activityId === "workflow-upgrade") {
        onUpgrade();
    } else if (activityId === "workflow-run") {
        onRun();
    } else if (activityId === "save-workflow") {
        await saveOrCreate();
    } else if (activityId === "save-workflow-as") {
        onSaveAs();
    } else if (activityId === "workflow-create") {
        await createNewWorkflow();
    }
}

function onAnnotation(nodeId: string, newAnnotation: string) {
    const step = steps.value[nodeId];
    if (step) {
        stepActions.setAnnotation(step, newAnnotation);
    }
}

async function routeToWorkflow(workflowId: string) {
    // map scoped stores to existing stores, before updating the id
    const { addScopePointer } = useScopePointerStore();
    addScopePointer(workflowId, id.value);

    id.value = workflowId;

    if (await onSave()) {
        hasChanges.value = false;
        router.replace({ query: { id: workflowId } });
    }
}

/**
 * Keeps the route's `version` query param in sync with the version currently loaded
 * in the editor (e.g. after a save, or after manually switching versions), without
 * triggering a reload of the editor.
 * @param version The version to sync to the route. If `undefined` or `null`, the `version` param is removed.
 * @param onlyIfPresent If `true`, the route is left untouched unless it already has a
 * `version` param (e.g. a save should not turn an implicit-latest URL into a pinned one).
 */
function syncVersionToRoute(version?: number, onlyIfPresent = false) {
    const currentVersionParam = route.query.version;
    if (onlyIfPresent && currentVersionParam === undefined) {
        return;
    }
    const newVersionParam = version === undefined || version === null ? undefined : String(version);
    if (currentVersionParam === newVersionParam) {
        return;
    }

    const query = { ...route.query };
    if (newVersionParam === undefined) {
        delete query.version;
    } else {
        query.version = newVersionParam;
    }
    emit("skipNextReload");
    router.replace({ query });
}

async function onCreate(): Promise<boolean> {
    if (!nameValidate()) {
        return false;
    }

    try {
        const { id: createdId, name: createdName, number_of_steps } = await services.createWorkflow(workflowData.value);
        const message = `Created new workflow '${createdName}' with ${number_of_steps} steps.`;
        hasChanges.value = false;

        emit("skipNextReload");

        await routeToWorkflow(createdId);

        Toast.success(message);
    } catch (e) {
        onWorkflowError("Creating workflow failed", errorMessageAsString(e, "Please contact an administrator."));
        return false;
    }
    return true;
}

function nameValidate() {
    if (!name.value) {
        Toast.error("Please provide a name for your workflow.");

        showAttributes();

        return false;
    }
    return true;
}

function onSetData(stepId: number, newData: object) {
    lastQueue
        .enqueue(() => getModule(newData, stepId, stateStore.setLoadingState), {})
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
            stepActions.updateStep(stepId, partialStep);
        });
}

function onLabel(nodeId: string, newLabel: string) {
    const step = steps.value[nodeId];
    if (step) {
        stepActions.setLabel(step, newLabel);
    }
}

function onUpgrade() {
    onAttemptRefactor([{ action_type: "upgrade_all_steps" }]);
}

async function generateAIReport() {
    if (blockedWhileLoading("generating the AI report")) {
        return;
    }

    if (hasChanges.value) {
        Toast.error("Please save your workflow before generating the AI report.");
        return;
    }

    if (!id.value || isNewTempWorkflow.value) {
        Toast.error("Workflow must be saved before generating the AI report.");
        return;
    }

    loadingWorkflow.value = true;
    try {
        const { model, report, total_tokens } = await generateAIReportFetch(id.value, version.value ?? undefined);
        onReportUpdate(report);
        Toast.success(
            `Report generated using ${model}${total_tokens ? `, total tokens used: ${total_tokens}` : ""}.`,
            "AI Report generated successfully.",
        );
    } catch (e) {
        onWorkflowError("Generating AI report failed", errorMessageAsString(e, "Please contact an administrator."));
    } finally {
        loadingWorkflow.value = false;
    }
}

function onReportUpdate(markdown: string) {
    hasChanges.value = true;
    report.value.markdown = markdown;
}

function onRun() {
    onNavigate(`/workflows/run?id=${id.value}`, false, false, true);
}

async function onNavigate(url: string, forceSave = false, ignoreChanges = false, appendVersion = false) {
    let proceed = false;
    if (hasChanges.value && !forceSave && !ignoreChanges) {
        // if there are changes, prompt user to save or discard or cancel
        navUrl.value = url;
        saveChangesAppendVersion.value = appendVersion;
        showSaveChangesModal.value = true;
    } else if (forceSave) {
        // when forceSave is true, save (or create, if this is a new unsaved workflow)
        // the workflow before navigating
        proceed = isNewTempWorkflow.value ? await onCreate() : await onSave();
    } else {
        // no changes to save, proceed with navigation
        proceed = true;
    }
    if (!proceed) {
        return;
    }

    if (appendVersion && version.value !== undefined && version.value !== null) {
        url += `&version=${version.value}`;
    }
    hasChanges.value = false;
    await nextTick();

    if (route.fullPath === url) {
        emit("forceReload");
    } else {
        router.push(url);
    }
}

/** Saves the workflow, and loads it onto the editor by calling `_loadCurrent`.
 * @returns true if save was successful, false otherwise
 */
async function onSave(): Promise<boolean> {
    if (!nameValidate()) {
        return false;
    }
    if (!hasChanges.value) {
        return true;
    }
    loadingWorkflow.value = true;
    const lastActiveNodeId = activeNodeId.value;

    try {
        const data = await saveWorkflow(workflowData.value);

        versions.value = await getVersions(id.value);

        name.value = data.name;
        version.value = data.version as number;
        annotation.value = data.annotation;

        hideErrorModal();

        // TODO: Should we add a Toast here?

        // If version is not defined, set it to the latest version
        const latestVersion = versions.value[versions.value.length - 1]?.version;
        if ((version.value === undefined || version.value === null) && latestVersion !== undefined) {
            version.value = latestVersion;
        }

        await loadCurrent(id.value, version.value);
        syncVersionToRoute(version.value, true);
    } catch (response) {
        onWorkflowError("Saving workflow failed...", errorMessageAsString(response));
        return false;
    } finally {
        stateStore.activeNodeId = lastActiveNodeId;
        loadingWorkflow.value = false;
    }
    return true;
}

async function onVersion(newVersion: number) {
    if (newVersion != version.value) {
        if (blockedWhileLoading("switching versions")) {
            return;
        }
        if (hasChanges.value) {
            const r = window.confirm("There are unsaved changes to your workflow which will be lost. Continue ?");
            if (r == false) {
                return;
            }
        }
        version.value = newVersion;
        syncVersionToRoute(newVersion);
        await loadCurrent(id.value, newVersion);
    }
}

async function insertStep(contentId: string, name: string, type: NewStep["type"], state?: any, toolUuid?: string) {
    const action = new InsertStepAction(stepStore, stateStore, {
        contentId,
        name,
        type,
        position: defaultPosition(graphOffset.value, transform.value),
    });

    undoRedoStore.applyAction(action);
    const stepData = action.getNewStepData();

    const response = await getModule(
        {
            name,
            type,
            content_id: contentId,
            tool_state: state,
            tool_uuid: toolUuid,
            // Request the latest version, mirroring what `routeToTool` does with `&version=latest`.
            // Without this, toolshed tools whose GUID includes the version would resolve to
            // that specific (possibly old) version rather than the latest.
            tool_version: type === "tool" && !toolUuid ? "latest" : undefined,
        },
        stepData.id,
        stateStore.setLoadingState,
    );

    const updatedStep = {
        ...stepData,
        tool_uuid: toolUuid,
        tool_state: response.tool_state,
        inputs: response.inputs,
        outputs: response.outputs,
        config_form: response.config_form,
        // Use the resolved content_id and tool_version from the response which
        // references the latest tool version, rather than what comes from the GUID
        content_id: response.content_id || stepData.content_id,
        tool_version: response.tool_version || stepData.tool_version,
    };

    stepStore.updateStep(updatedStep);
    action.updateStepData = updatedStep;

    stateStore.activeNodeId = stepData.id;
}

async function loadEditorData(data: any) {
    if (data.name !== undefined) {
        name.value = data.name;
    }
    if (data.annotation !== undefined) {
        annotation.value = data.annotation;
    }
    if (data.readme !== undefined) {
        readme.value = data.readme;
    }
    if (data.help !== undefined) {
        help.value = data.help;
    }
    if (data.logo_url !== undefined) {
        logoUrl.value = data.logo_url;
    }
    if (data.version !== undefined) {
        version.value = data.version;
    }

    const newReport = data.report || {};
    const markdown = newReport.markdown || reportDefault;
    report.value.markdown = markdown;

    hideErrorModal();

    stateMessages.value = getStateUpgradeMessages(data);
    const hasStateMessages = stateMessages.value.length > 0;
    tags.value = data.tags;
    license.value = data.license;
    creator.value = data.creator;
    doi.value = data.doi;

    try {
        versions.value = await getVersions(id.value);
    } catch (e) {
        onWorkflowError("Loading workflow versions failed...", errorMessageAsString(e));
    } finally {
        await nextTick();
        hasChanges.value = hasStateMessages;
    }
}

/**
 * Fetches and loads the workflow data for the given id and version into the editor.
 * @param workflowId The workflow ID
 * @param workflowVersion The workflow version number
 * @param fitGraph Whether to reset the workflow transform and positioning to the default fit
 */
async function loadCurrent(workflowId: string, workflowVersion?: number | null, fitGraph = false) {
    if (!isNewTempWorkflow.value) {
        loadingWorkflow.value = true;

        try {
            // Store the current transform and bounding box before loading; to adjust for coordinate shifts
            const { transform: transformBefore, bounds: boundsBefore } = captureTransformAndBounds(transform.value);
            try {
                // Load editor view workflow data
                const data = await lastQueue.enqueue(
                    async () => getWorkflowFull(workflowId, workflowVersion ?? undefined),
                    {},
                );

                // Reset stores and load new data onto editor
                await resetStores();
                await fromSimple(workflowId, data);
                await loadEditorData(data);
            } catch (e) {
                onWorkflowError("Loading workflow failed...", errorMessageAsString(e));
            }

            await until(() => datatypesMapperLoading.value).toBe(false);
            await nextTick();

            if (fitGraph) {
                workflowGraph.value?.fitWorkflow();
            } else {
                // If we are not fitting the graph, adjust for coordinate shifts so the nodes appear in the same position
                adjustForCoordinateShift(transformBefore, boundsBefore);
            }
        } finally {
            loadingWorkflow.value = false;
        }
    }
}

/**
 * Adjusts the workflow graph transform to account for coordinate shifts that may be
 * computed by the backend when a workflow step order/positioning changes.
 * @param transformBefore The transform we had before refetching the workflow
 * @param boundsBefore The bounding box min coordinates we had before refetching the workflow
 */
function adjustForCoordinateShift(transformBefore: WorkflowTransform, boundsBefore: BoundingBoxBounds) {
    const adjustedTransform = calculateAdjustedTransform(transformBefore, boundsBefore);

    // TODO: Once we migrate to Composition API we can probably handle this within the workflowBoundingBox
    // and d3Zoom composables
    workflowGraph.value?.setTransform(adjustedTransform);

    // TODO: Verify if setting scale is still needed after setting full transform
    //       I still needed to set scale separately otherwise it would reset to 1
    stateStore.scale = adjustedTransform.k;
}

function onLicense(lc: string) {
    if (license.value != lc) {
        hasChanges.value = true;
        setLicense(lc);
    }
}

function onCreator(cr: Creator[]) {
    if (!isEqual(creator.value, cr)) {
        hasChanges.value = true;
        setCreator(cr);
    }
}

function onDoi(newDoi: string[] | null) {
    if (doi.value != newDoi) {
        hasChanges.value = true;
        setDoi(newDoi);
    }
}

/** Calls the `loadCurrent` function to load the workflow data into the editor when the component is mounted. */
async function initializeWorkflowEditor() {
    await loadCurrent(id.value, version.value, true);

    initialLoading.value = false;
}
initializeWorkflowEditor();
</script>

<template>
    <div class="workflow-editor">
        <StateUpgradeModal :state-messages="stateMessages" />

        <StateUpgradeModal
            :state-messages="insertedStateMessages"
            title="Subworkflow embedded with changes"
            message="Problems were encountered loading this workflow (possibly a result of tool upgrades). Please review the following parameters and then save." />

        <RefactorConfirmationModal
            :workflow-id="id"
            :version="version ?? undefined"
            :versions="versions"
            :refactor-actions="refactorActions"
            :loading.sync="loadingWorkflow"
            @onWorkflowError="onWorkflowError"
            @onRefactor="onRefactor"
            @onShow="hideErrorModal" />

        <GModal
            data-description="workflow editor error modal"
            :show="Boolean(errorMessageBody)"
            size="small"
            :title="errorMessageTitle || 'Workflow Editor Error'"
            @close="hideErrorModal">
            <GAlert variant="danger">{{ errorMessageBody }}</GAlert>
        </GModal>

        <SaveChangesModal
            :append-version="saveChangesAppendVersion"
            :nav-url="navUrl"
            :show-modal.sync="showSaveChangesModal"
            @on-proceed="onNavigate" />

        <GModal
            :show.sync="showSaveAsModal"
            confirm
            size="small"
            data-description="save-as-modal"
            title="Save As a New Workflow"
            ok-text="Save"
            @ok="doSaveAs"
            @cancel="resetSaveAs">
            <GForm @submit.native.prevent="doSaveAs">
                <GFormLabel title="Name">
                    <GFormInput v-model="saveAsName" />
                </GFormLabel>
                <GFormLabel title="Annotation">
                    <BFormTextarea v-model="saveAsAnnotation" />
                </GFormLabel>
            </GForm>
        </GModal>

        <ActivityBar
            ref="activityBar"
            data-description="workflow editor activity bar"
            :default-activities="workflowActivities"
            :special-activities="[bestPracticesActivity]"
            :exit-activity="exitWorkflowActivity"
            :run-activity="runWorkflowActivity"
            activity-bar-id="workflow-editor"
            :show-admin="false"
            options-title="Options"
            options-heading="Workflow Options"
            options-tooltip="View additional workflow options"
            options-search-placeholder="Search options"
            initial-activity="workflow-editor-attributes"
            :options-icon="faCog"
            :hide-panel="reportActive || initialLoading"
            :header-icon="faSitemap"
            header-title="Editor"
            @activityClicked="onActivityClicked">
            <template v-slot:side-panel>
                <ToolPanel v-if="isActiveSideBar('workflow-editor-tools')" workflow @onInsertTool="onInsertTool" />
                <SearchPanel
                    v-else-if="isActiveSideBar('workflow-editor-search')"
                    @result-clicked="onHighlightRegion" />
                <InputPanel
                    v-else-if="isActiveSideBar('workflow-editor-inputs')"
                    :inputs="inputs"
                    @insertModule="onInsertModule" />
                <WorkflowLint
                    v-else-if="isActiveSideBar('workflow-best-practices')"
                    :lint-data="lintData"
                    :steps="steps"
                    :has-changes="hasChanges"
                    :on-save="onSave"
                    @onAttributes="
                        (e) => {
                            showAttributes(e);
                        }
                    "
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
                    :highlight.sync="highlightAttribute"
                    :parameters="parameters"
                    :annotation="annotation"
                    :name="name"
                    :version="version ?? undefined"
                    :versions="versions"
                    :license="license"
                    :creator="creator || undefined"
                    :doi="doi || undefined"
                    :logo-url="logoUrl"
                    :help="help"
                    :readme-active.sync="readmeActive"
                    @version="onVersion"
                    @tags="setTags"
                    @license="onLicense"
                    @creator="onCreator"
                    @doi="onDoi"
                    @update:nameCurrent="setName"
                    @update:annotationCurrent="setAnnotation"
                    @update:logoUrlCurrent="setLogoUrl"
                    @update:helpCurrent="setHelp" />
                <UserToolPanel
                    v-if="isActiveSideBar('workflow-editor-user-defined-tools')"
                    :in-workflow-editor="true"
                    in-panel
                    @onInsertTool="onInsertTool" />
            </template>
        </ActivityBar>

        <template v-if="reportActive">
            <MarkdownEditor
                :markdown-text="report.markdown ?? ''"
                mode="report"
                :title="'Workflow Report Template: ' + name"
                :labels="getLabels"
                :loading="loadingWorkflow"
                :steps="steps"
                @update="onReportUpdate">
                <template v-slot:buttons>
                    <GButton
                        tooltip
                        title="Generate AI GalaxyAI report based on the workflow and its expected results"
                        disabled-title="Please wait for the workflow to finish loading"
                        variant="link"
                        color="blue"
                        transparent
                        size="large"
                        :disabled="loadingWorkflow"
                        @click="generateAIReport">
                        <FontAwesomeIcon :icon="faMagic" />
                    </GButton>

                    <GButton
                        id="workflow-canvas-button"
                        title="Return to Workflow"
                        tooltip
                        transparent
                        size="large"
                        @click="showAttributes">
                        <FontAwesomeIcon :icon="faTimes" />
                    </GButton>
                </template>
            </MarkdownEditor>
        </template>
        <template v-else>
            <div id="center" class="workflow-center">
                <div class="editor-top-bar" unselectable="on">
                    <span>
                        <span class="sr-only">Workflow Editor</span>
                        <LoadingSpan v-if="initialLoading" message="Loading Editor" />
                        <span v-else class="editor-title" :title="name">
                            {{ name }}
                            <i v-if="hasChanges" class="text-muted"> (unsaved changes) </i>
                        </span>
                    </span>

                    <div class="d-flex align-items-center flex-gapx-1">
                        <BDropdown
                            v-if="credentialSteps.length > 0"
                            no-caret
                            right
                            variant="link"
                            style="z-index: 60000"
                            title="Workflow contains steps that require credentials"
                            @show="() => (showCredentialsDropdown = true)"
                            @hide="() => (showCredentialsDropdown = false)">
                            <template v-slot:button-content>
                                <FontAwesomeIcon :icon="faKey" fixed-width />
                            </template>

                            <BDropdownText style="min-width: 25rem">
                                This workflow contains the following steps that require credentials:
                            </BDropdownText>

                            <BDropdownDivider />

                            <BDropdownItem
                                v-for="cs in credentialSteps"
                                :key="cs.id"
                                title="Click to go to step"
                                class="mr-0"
                                @click="onToolClick(cs.id)">
                                <FontAwesomeIcon :icon="faWrench" fixed-width />
                                {{ cs.id + 1 }}: {{ cs.label ?? cs.name }}
                            </BDropdownItem>
                        </BDropdown>

                        <GButtonGroup>
                            <GButton
                                :title="undoRedoStore.undoText + ' (Ctrl + Z)'"
                                :transparent="!undoRedoStore.hasUndo || loadingWorkflow"
                                size="large"
                                :disabled="!undoRedoStore.hasUndo || loadingWorkflow"
                                @click="undoRedoStore.undo()">
                                <FontAwesomeIcon :icon="faUndo" />
                            </GButton>
                            <GButton
                                :title="undoRedoStore.redoText + ' (Ctrl + Shift + Z)'"
                                :transparent="!undoRedoStore.hasRedo || loadingWorkflow"
                                size="large"
                                :disabled="!undoRedoStore.hasRedo || loadingWorkflow"
                                @click="undoRedoStore.redo()">
                                <FontAwesomeIcon :icon="faRedo" />
                            </GButton>
                        </GButtonGroup>

                        <GButton
                            id="workflow-save-button"
                            size="large"
                            color="blue"
                            :disabled="!hasChanges || loadingWorkflow"
                            :disabled-title="saveWorkflowTitle"
                            :title="saveWorkflowTitle"
                            tooltip
                            transparent
                            @click="saveOrCreate">
                            <FontAwesomeIcon :icon="faSave" />
                        </GButton>
                    </div>
                </div>

                <ReadmeEditor
                    v-if="readmeActive"
                    class="p-2"
                    :readme="readme"
                    :name="name"
                    :logo-url="logoUrl"
                    @exit="readmeActive = false"
                    @update:readmeCurrent="setReadme" />

                <WorkflowGraph
                    v-if="!datatypesMapperLoading && datatypesMapper"
                    v-show="!readmeActive"
                    ref="workflowGraph"
                    data-description="workflow graph in editor"
                    :steps="steps"
                    :datatypes-mapper="datatypesMapper"
                    :scroll-to-id="scrollToId"
                    :initial-position="{ x: 50, y: 50 }"
                    :loading="loadingWorkflow || initialLoading"
                    @scrollTo="scrollToId = null"
                    @transform="(value) => (transform = value)"
                    @graph-offset="(value) => (graphOffset = value)"
                    @onClone="onClone"
                    @onCreate="onInsertTool"
                    @onChange="hasChanges = true"
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
                        @editSubworkflow="onEditSubWorkflow"
                        @attemptRefactor="onAttemptRefactor"
                        @close="activeNodeId = null" />
                </WorkflowGraph>
            </div>
        </template>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.workflow-editor {
    display: flex;
    flex: 1;
    overflow: hidden;
    position: relative;

    .workflow-center {
        z-index: 0;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
        overflow: auto;
        width: 100%;

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
    }
}
</style>
