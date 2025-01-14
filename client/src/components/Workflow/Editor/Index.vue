<script setup lang="ts">
import { faArrowLeft, faArrowRight, faCog, faSave, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useMagicKeys, whenever } from "@vueuse/core";
import { logicAnd, logicNot, logicOr } from "@vueuse/math";
import { BButton, BButtonGroup, BFormGroup, BFormInput, BFormTextarea, BModal } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, nextTick, onMounted, onUnmounted, ref, unref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { type components } from "@/api/schema";
import { type StoredWorkflowDetailed } from "@/api/workflows";
import { InsertStepAction, useStepActions } from "@/components/Workflow/Editor/Actions/stepActions";
import { CopyIntoWorkflowAction, SetValueActionHandler } from "@/components/Workflow/Editor/Actions/workflowActions";
import { defaultPosition } from "@/components/Workflow/Editor/composables/useDefaultStepPosition";
import {
    useActivityLogic,
    useSpecialWorkflowActivities,
    workflowEditorActivities,
} from "@/components/Workflow/Editor/modules/activities";
import type { WorkflowInput } from "@/components/Workflow/Editor/modules/inputs";
import { fromSimple } from "@/components/Workflow/Editor/modules/model";
import { getUntypedWorkflowParameters, type UntypedParameters } from "@/components/Workflow/Editor/modules/parameters";
import { getModule, getVersions, loadWorkflow, saveWorkflow } from "@/components/Workflow/Editor/modules/services";
import { getStateUpgradeMessages } from "@/components/Workflow/Editor/modules/utilities";
import reportDefault from "@/components/Workflow/Editor/reportDefault";
import { Services } from "@/components/Workflow/services";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { Toast } from "@/composables/toast";
import { useUid } from "@/composables/utils/uid";
import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import { getAppRoot } from "@/onload/loadConfig";
import { useScopePointerStore } from "@/stores/scopePointerStore";
import type { NewStep, PostJobActions, Step } from "@/stores/workflowStepStore";
import { LastQueue } from "@/utils/lastQueue";
import { errorMessageAsString } from "@/utils/simple-error";

import { getWorkflowInputs } from "./modules/inputs";

import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import MarkdownEditor from "@/components/Markdown/MarkdownEditor.vue";
import InputPanel from "@/components/Panels/InputPanel.vue";
import ToolPanel from "@/components/Panels/ToolPanel.vue";
import WorkflowPanel from "@/components/Panels/WorkflowPanel.vue";
import UndoRedoStack from "@/components/UndoRedo/UndoRedoStack.vue";
import WorkflowLint from "@/components/Workflow/Editor/Lint.vue";
import MessagesModal from "@/components/Workflow/Editor/MessagesModal.vue";
import NodeInspector from "@/components/Workflow/Editor/NodeInspector.vue";
import RefactorConfirmationModal from "@/components/Workflow/Editor/RefactorConfirmationModal.vue";
import SaveChangesModal from "@/components/Workflow/Editor/SaveChangesModal.vue";
import StateUpgradeModal from "@/components/Workflow/Editor/StateUpgradeModal.vue";
import WorkflowAttributes from "@/components/Workflow/Editor/WorkflowAttributes.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";

type Creator =
    | (components["schemas"]["Person"] | components["schemas"]["galaxy__schema__schema__Organization"])[]
    | null;

interface Props {
    dataManagers: any[];
    moduleSections: any[];
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
}>();

const { ctrl_z, ctrl_shift_z, meta_z, meta_shift_z } = useMagicKeys();

const services = new Services();
const lastQueue = new LastQueue();

const undoKeys = logicOr(ctrl_z, meta_z);
const redoKeys = logicOr(ctrl_shift_z, meta_shift_z);

const router = useRouter();
const inputs = getWorkflowInputs();
const { confirm } = useConfirmDialog();
const { datatypes, datatypesMapper, datatypesMapperLoading } = useDatatypesMapper();

const uid = unref(useUid("workflow-editor-"));

const id = ref(props.workflowId || uid);
const name = ref("Unnamed Workflow");
const license = ref("");
const versions = ref([]);
const tags = ref<string[]>([]);
const creator = ref<Creator>();
const saveAsName = ref<string>();
const annotation = ref<string>("");
const version = ref<number>(props.initialVersion);
const navUrl = ref("");

const parameters = ref<UntypedParameters>();

const markdownEditor = ref<any>(null);
const refactorActions = ref<any[]>([]);

const initialLoading = ref(true);
const highlightId = ref<string>();
const activityBar = ref<any>(null);
const stateMessages = ref<any[]>([]);
const scrollToId = ref<string | null>();
const insertedStateMessages = ref<string[]>([]);
const rightPanelElement = ref<HTMLElement | null>(null);

const showSaveAsModal = ref(false);
const saveAsAnnotation = ref(null);
const messageIsError = ref(false);
const showSaveChangesModal = ref(false);
const highlightAttribute = ref<string | undefined>();
const messageBody = ref<string | undefined>();
const messageTitle = ref<string | undefined>();
const transform = ref({ x: 0, y: 0, k: 1 });
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

const { connectionStore, stepStore, stateStore, commentStore, undoRedoStore } = provideScopedWorkflowStores(id.value);

const { undo, redo } = undoRedoStore;
const { steps } = storeToRefs(stepStore);
const { report } = storeToRefs(stateStore);
const { activeNodeId } = storeToRefs(stateStore);

const { comments } = storeToRefs(commentStore);

const setNameActionHandler = new SetValueActionHandler(
    undoRedoStore,
    (value) => (name.value = value as string),
    showAttributes,
    "set workflow name"
);

const setAnnotationHandler = new SetValueActionHandler(
    undoRedoStore,
    (value) => (annotation.value = value as string),
    showAttributes,
    "modify annotation"
);

const setTagsHandler = new SetValueActionHandler(
    undoRedoStore,
    (value) => (tags.value = structuredClone(value) as string[]),
    showAttributes,
    "change tags"
);

const setLicenseHandler = new SetValueActionHandler(
    undoRedoStore,
    (value) => (license.value = value as string),
    showAttributes,
    "set license"
);

whenever(logicAnd(undoKeys, logicNot(redoKeys)), undo);
whenever(redoKeys, redo);

const setCreatorHandler = new SetValueActionHandler(
    undoRedoStore,
    (value) => (creator.value = value as Creator),
    showAttributes,
    "set creator"
);

const { hasChanges } = storeToRefs(stateStore);

const isNewTempWorkflow = computed(() => !props.workflowId);
const reportActive = computed(() => isActiveSideBar("workflow-editor-report"));
const hasInvalidConnections = computed(() => Object.keys(connectionStore.invalidConnections).length > 0);
const activeStep = computed(() => {
    if (activeNodeId.value !== null) {
        return stepStore.getStep(activeNodeId.value);
    }
    return null;
});
const saveWorkflowTitle = computed(() =>
    hasInvalidConnections.value
        ? "Workflow has invalid connections, review and remove invalid connections"
        : "Save Workflow"
);
const workflowData = computed<Partial<StoredWorkflowDetailed>>(() => ({
    name: name.value,
    annotation: annotation.value,
    comments: comments.value,
    license: license.value,
    creator: creator.value,
    tags: tags.value,
    report: report.value,
    steps: steps.value as any,
}));

const { specialWorkflowActivities } = useSpecialWorkflowActivities(
    computed(() => ({
        hasInvalidConnections: hasInvalidConnections.value,
    }))
);

useActivityLogic(
    computed(() => ({
        activityBarId: "workflow-editor",
        isNewTempWorkflow: isNewTempWorkflow.value,
    }))
);

const stepActions = useStepActions(stepStore, undoRedoStore, stateStore, connectionStore);

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

function isActiveSideBar(activityBarId: string) {
    return activityBar.value?.isActiveSideBar(activityBarId);
}

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

/** user set name. queues an undo/redo action */
function setName(newName: string) {
    if (name.value !== newName) {
        setNameActionHandler.set(name.value, newName);
    }
}

/** user set license. queues an undo/redo action */
function setLicense(newLicense: string) {
    if (license.value !== newLicense) {
        setLicenseHandler.set(license.value, newLicense);
    }
}

/** user set creator. queues an undo/redo action */
function setCreator(newCreator?: unknown[]) {
    setCreatorHandler.set(creator.value, newCreator);
}

/** user set annotation. queues an undo/redo action */
function setAnnotation(newAnnotation: string) {
    if (annotation.value !== newAnnotation) {
        setAnnotationHandler.set(annotation.value, newAnnotation);
    }
}

function setTags(newTags: string[]) {
    setTagsHandler.set(tags.value, newTags);
}

function scrollToTop() {
    rightPanelElement.value?.scrollTo({
        top: 0,
        behavior: "instant",
    });
}

function insertMarkdown(markdown: any) {
    markdownEditor.value?.insertMarkdown(markdown);
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

function setModalMessage(title?: string, body?: string, isError?: boolean) {
    messageTitle.value = title;
    messageBody.value = body;
    messageIsError.value = !!isError;
}

function onChange() {
    hasChanges.value = true;
}

function onChangePostJobActions(nodeId: number, postJobActions: PostJobActions) {
    const partialStep = { post_job_actions: postJobActions };
    stepActions.updateStep(nodeId, partialStep);
}

function onRemove(nodeId: string) {
    const tmpStep = steps.value[nodeId];

    if (tmpStep) {
        stepActions.removeStep(tmpStep);
    }
}

function onEditSubWorkflow(contentId: string) {
    const editUrl = `/workflows/edit?workflow_id=${contentId}`;

    onNavigate(editUrl);
}

function onInsertTool(toolId: string, toolName: string) {
    insertStep(toolId, toolName, "tool");
}

function onInsertModule(moduleId: Step["type"], moduleName: string, state: WorkflowInput["stateOverwrites"]) {
    insertStep(moduleName, moduleName, moduleId, state);
}

async function onInsertWorkflow(workflowId: string, workflowName: string, state: any) {
    insertStep(workflowId, workflowName, "subworkflow", state);
}

async function copyIntoWorkflow(workflowId: string) {
    try {
        const data = await loadWorkflow({ id: workflowId });

        const action = new CopyIntoWorkflowAction(
            id.value,
            data,
            defaultPosition(graphOffset.value, transform.value)
        );

        undoRedoStore.applyAction(action);

        // Determine if any parameters were 'upgraded' and provide message

        const insertedStateMessages = getStateUpgradeMessages(data);

        onInsertedStateMessages(insertedStateMessages);
    } catch (e) {
        setModalMessage("Importing workflow failed", errorMessageAsString(e));
    }
}

function onDownload() {
    window.location.href = `${getAppRoot()}api/workflows/${id.value}/download?format=json-download`;
}

function onSaveAs() {
    showSaveAsModal.value = true;
}

function onAnnotation(nodeId: string, newAnnotation: string) {
    const step = steps.value[nodeId];
    if (step) {
        stepActions.setAnnotation(step, newAnnotation);
    }
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

function onScrollTo(stepId: string) {
    scrollToId.value = stepId;
    onHighlight(stepId);
}

function onHighlight(stepId: string) {
    highlightId.value = stepId;
}

function onUnhighlight() {
    highlightId.value = "";
}

function onUpgrade() {
    onAttemptRefactor([{ action_type: "upgrade_all_steps" }]);
}

function onReportUpdate(markdown: string) {
    hasChanges.value = true;
    report.value.markdown = markdown;
}

function onRun() {
    onNavigate(`/workflows/run?id=${id.value}`, false, false, true);
}

function onVersion(vr: number) {
    if (vr != version.value) {
        if (hasChanges.value) {
            const confirmed = confirm("There are unsaved changes to your workflow which will be lost. Continue ?");

            if (!confirmed) {
                return;
            }
        }

        version.value = vr;

        loadCurrent(id.value, vr);
    }
}

async function insertStep(contentId: string, name: string, type: NewStep["type"], state?: any) {
    const action = new InsertStepAction(stepStore, stateStore, {
        contentId,
        name,
        type,
        position: defaultPosition(graphOffset.value, transform.value),
    });

    undoRedoStore.applyAction(action);
    const stepData = action.getNewStepData();

    const response = await getModule(
        { name, type, content_id: contentId, tool_state: state },
        stepData.id,
        stateStore.setLoadingState
    );

    const updatedStep = {
        ...stepData,
        tool_state: response.tool_state,
        inputs: response.inputs,
        outputs: response.outputs,
        config_form: response.config_form,
    };

    stepStore.updateStep(updatedStep);
    action.updateStepData = updatedStep;
    stateStore.activeNodeId = stepData.id;
}

function onLicense(lc: string) {
    if (license.value != lc) {
        hasChanges.value = true;
        setLicense(lc);
    }
}

function onCreator(cr: unknown[]) {
    if (creator.value != cr) {
        hasChanges.value = true;

        setCreator(cr);
    }
}

function onInsertedStateMessages(messages: string[]) {
    insertedStateMessages.value = messages;
    setModalMessage();
}

async function onRefactor(response: { workflow: any }) {
    await resetStores();
    await fromSimple(id.value, response.workflow);

    loadEditorData(response.workflow);
}

async function createNewWorkflow() {
    await saveOrCreate();

    router.push("/workflows/edit");
}

async function saveOrCreate() {
    if (hasInvalidConnections.value) {
        const confirmed = await confirm(
            `Workflow has invalid connections. You can save the workflow, but it may not run correctly.`,
            {
                id: "save-workflow-confirmation",
                okTitle: "Save Workflow",
            }
        );

        if (confirmed) {
            emitSaveOrCreate();
        }
    } else {
        emitSaveOrCreate();
    }
}

async function emitSaveOrCreate() {
    if (isNewTempWorkflow.value) {
        await onCreate();
    } else {
        await onSave();
    }
}

async function resetStores() {
    hasChanges.value = false;
    connectionStore.$reset();
    stepStore.$reset();
    stateStore.$reset();
    commentStore.$reset();
    undoRedoStore.$reset();
    await nextTick();
}

async function loadEditorData(data: any) {
    if (data.name !== undefined) {
        name.value = data.name;
    }

    if (data.annotation !== undefined) {
        annotation.value = data.annotation;
    }

    if (data.version !== undefined) {
        version.value = data.version;
    }

    const rp = data.report || {};
    const markdown = rp.markdown || reportDefault;

    rp.markdown = markdown;

    setModalMessage();

    stateMessages.value = getStateUpgradeMessages(data);

    license.value = data.license;
    creator.value = data.creator;

    const vs = await getVersions(id.value);
    versions.value = vs;

    hasChanges.value = stateMessages.value.length > 0;
}

async function onAttemptRefactor(actions: any[]) {
    if (hasChanges.value) {
        const confirmed = await confirm(
            "You've made changes to your workflow that need to be saved before attempting the requested action. Save those changes and continue?"
        );

        if (!confirmed) {
            return;
        }

        setModalMessage("Saving workflow...", "progress");

        try {
            const data = await saveWorkflow(id.value, workflowData.value);

            name.value = data.name;
            version.value = data.version;
            annotation.value = data.annotation;

            refactorActions.value = actions;
            hasChanges.value = false;
        } catch (e) {
            setModalMessage("Saving workflow failed, cannot apply requested changes...", errorMessageAsString(e));
        }
    } else {
        refactorActions.value = actions;
    }
}

async function onClone(stepId: string) {
    const sourceStep = steps.value[parseInt(stepId)];
    if (sourceStep) {
        const newStep = {
            ...sourceStep,
            uuid: undefined,
            position: defaultPosition(graphOffset.value, transform.value),
        };

        stepActions.copyStep(newStep);
    }
}

async function onInsertWorkflowSteps(workflowId: string, stepCount?: number) {
    if (stepCount && stepCount < 10) {
        copyIntoWorkflow(workflowId);
    } else {
        const confirmed = await confirm(
            `Warning this will add ${stepCount} new steps into your current workflow.  You may want to consider using a subworkflow instead.`
        );

        if (confirmed) {
            copyIntoWorkflow(workflowId);
        }
    }
}

async function doSaveAs() {
    if (!saveAsName.value && !nameValidate()) {
        return;
    }

    const rename_name = saveAsName.value ?? `SavedAs_${name.value}`;
    const rename_annotation = saveAsAnnotation.value ?? "";

    try {
        const newSaveAsWf = { id: id.value, name: rename_name, annotation: rename_annotation };
        const { id: newId, name, number_of_steps } = await services.createWorkflow(newSaveAsWf);

        hasChanges.value = false;

        await routeToWorkflow(newId);

        Toast.success(`Created new workflow '${name}' with ${number_of_steps} steps.`);
    } catch (e) {
        const errorHeading = `Saving workflow as '${rename_name}' failed`;

        setModalMessage(errorHeading, errorMessageAsString(e) || "Please contact an administrator.");
    }
}

async function onActivityClicked(activityId: string) {
    if (activityId === "save-and-exit") {
        await saveOrCreate();
        router.push("/workflows/list");
    } else if (activityId === "exit") {
        router.push("/workflows/list");
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
        createNewWorkflow();
    }
}

async function routeToWorkflow(workflowId: string) {
    // map scoped stores to existing stores, before updating the id
    const { addScopePointer } = useScopePointerStore();
    addScopePointer(workflowId, id.value);

    id.value = workflowId;

    await onSave();

    hasChanges.value = false;
    router.push({ query: { id: id.value } });
}

async function onCreate() {
    if (!nameValidate()) {
        return;
    }

    try {
        const { id: wId, name, number_of_steps } = await services.createWorkflow(workflowData.value);
        const message = `Created new workflow '${name}' with ${number_of_steps} steps.`;
        hasChanges.value = false;

        emit("skipNextReload");

        await routeToWorkflow(wId);

        Toast.success(message);
    } catch (e) {
        setModalMessage("Creating workflow failed", errorMessageAsString(e) || "Please contact an administrator.");
    }
}

async function onNavigate(url: string, forceSave = false, ignoreChanges = false, appendVersion = false) {
    if (isNewTempWorkflow.value) {
        await onCreate();
    } else if (hasChanges.value && !forceSave && !ignoreChanges) {
        // if there are changes, prompt user to save or discard or cancel
        navUrl.value = url;
        showSaveChangesModal.value = true;

        return;
    } else if (forceSave) {
        // when forceSave is true, save the workflow before navigating
        await onSave();
    }

    if (appendVersion && version.value !== undefined) {
        url += `&version=${version.value}`;
    }

    hasChanges.value = false;

    await nextTick();

    router.push(url);
}

async function onSave(hideProgress = false) {
    if (!nameValidate()) {
        return;
    }

    !hideProgress && setModalMessage("Saving workflow...", "progress");

    try {
        const data = await saveWorkflow(id.value, workflowData.value);
        name.value = data.name;
        version.value = data.version;
        annotation.value = data.annotation;

        const vs = await getVersions(id.value);
        versions.value = vs;

        setModalMessage();

        Toast.success("Workflow saved successfully.");

        hasChanges.value = false;
    } catch (e) {
        setModalMessage("Saving workflow failed...", errorMessageAsString(e));
    }
}

async function loadCurrent(cId: string, v?: number) {
    if (!isNewTempWorkflow.value) {
        await resetStores();

        setModalMessage("Loading workflow...", "progress");

        try {
            const data = await lastQueue.enqueue(loadWorkflow, { id: cId, version: v });

            await fromSimple(cId, data);

            await loadEditorData(data);
        } catch (e) {
            setModalMessage("Loading workflow failed...", errorMessageAsString(e));
        }
    }
}

watch(
    () => props.initialVersion,
    (newVal, oldVal) => {
        if (newVal != oldVal && oldVal === undefined) {
            version.value = props.initialVersion;
        }
    }
);

watch(
    () => props.workflowTags,
    (newTags) => {
        tags.value = [...newTags];
    },
    { immediate: true }
);

watch(
    () => id.value,
    (newId, oldId) => {
        if (oldId) {
            loadCurrent(newId);
        }
    }
);

watch(
    () => name.value,
    (newName, oldName) => {
        if (newName != oldName) {
            hasChanges.value = true;
        }
    }
);

watch(
    () => annotation.value,
    (newAnnotation, oldAnnotation) => {
        if (newAnnotation != oldAnnotation) {
            hasChanges.value = true;
        }
    }
);

watch(
    () => hasChanges.value,
    (newHasChanges) => {
        emit("update:confirmation", newHasChanges);
    }
);
watch(
    () => stateStore.activeNodeId,
    () => {
        scrollToTop();
    }
);

onMounted(async () => {
    await loadCurrent(id.value, version.value);

    setModalMessage();

    initialLoading.value = false;
});

onUnmounted(async () => {
    await resetStores();

    emit("update:confirmation", false);
});
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
            :refactor-actions="refactorActions"
            @onWorkflowError="setModalMessage"
            @onWorkflowMessage="setModalMessage"
            @onRefactor="onRefactor"
            @onShow="setModalMessage" />

        <MessagesModal
            :title="messageTitle"
            :message="messageBody"
            :error="messageIsError"
            @onHidden="setModalMessage" />

        <SaveChangesModal :nav-url.sync="navUrl" :show-modal.sync="showSaveChangesModal" @on-proceed="onNavigate" />

        <BModal
            v-model="showSaveAsModal"
            title="Save As a New Workflow"
            ok-title="Save"
            cancel-title="Cancel"
            @ok="doSaveAs">
            <BFormGroup label="Name">
                <BFormInput v-model="saveAsName" />
            </BFormGroup>

            <BFormGroup label="Annotation">
                <BFormTextarea v-model="saveAsAnnotation" />
            </BFormGroup>
        </BModal>

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
            <template v-slot:side-panel>
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
                    @onAttributes="(e) => showAttributes(e)"
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
                    @version="onVersion"
                    @tags="setTags"
                    @license="onLicense"
                    @creator="onCreator"
                    @update:nameCurrent="setName"
                    @update:annotationCurrent="setAnnotation" />
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
                    <BButton
                        id="workflow-canvas-button"
                        v-b-tooltip.hover.bottom
                        title="Return to Workflow"
                        variant="link"
                        role="button"
                        @click="showAttributes">
                        <FontAwesomeIcon :icon="faTimes" />
                    </BButton>
                </template>
            </MarkdownEditor>
        </template>
        <template v-else>
            <div id="center" class="workflow-center">
                <div class="editor-top-bar" unselectable="on">
                    <span>
                        <span class="sr-only">Workflow Editor</span>
                        <span class="editor-title" :title="name">
                            {{ name }}
                            <i v-if="hasChanges" class="text-muted"> (unsaved changes) </i>
                            <BButton
                                v-if="hasChanges"
                                id="workflow-save-button"
                                v-b-tooltip.hover.bottom
                                class="py-1 px-2"
                                variant="link"
                                :title="saveWorkflowTitle"
                                @click="saveOrCreate">
                                <FontAwesomeIcon :icon="faSave" />
                            </BButton>
                        </span>
                    </span>

                    <BButtonGroup>
                        <BButton
                            :title="undoRedoStore.undoText + ' (Ctrl + Z)'"
                            :variant="undoRedoStore.hasUndo ? 'secondary' : 'muted'"
                            @click="undoRedoStore.undo()">
                            <FontAwesomeIcon :icon="faArrowLeft" />
                        </BButton>
                        <BButton
                            :title="undoRedoStore.redoText + ' (Ctrl + Shift + Z)'"
                            :variant="undoRedoStore.hasRedo ? 'secondary' : 'muted'"
                            @click="undoRedoStore.redo()">
                            <FontAwesomeIcon :icon="faArrowRight" />
                        </BButton>
                    </BButtonGroup>
                </div>

                <WorkflowGraph
                    v-if="!datatypesMapperLoading"
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
                        @editSubworkflow="onEditSubWorkflow"
                        @attemptRefactor="onAttemptRefactor"
                        @close="activeNodeId = null"></NodeInspector>
                </WorkflowGraph>
            </div>
        </template>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

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
