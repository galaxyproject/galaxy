<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { canMutateHistory as canMutateHistoryMethod } from "@/api";
import type { JobRequest, JobResponse } from "@/api/jobs";
import type { FormData, FormInputNode } from "@/components/Form/composables/useFormState";
import type { DataOption } from "@/components/Form/Elements/FormData/types";
import { findInputByDottedName } from "@/components/Form/utilities";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { useConfigStore } from "@/stores/configurationStore";
import { useHistoryItemsStore } from "@/stores/historyItemsStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useJobStore } from "@/stores/jobStore";
import { useTourStore } from "@/stores/tourStore";
import { useUserStore } from "@/stores/userStore";
import { useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";
import localize from "@/utils/localization";
import { parseBool } from "@/utils/parseBool";
import { errorMessageAsString } from "@/utils/simple-error";

import { getToolFormData, updateToolFormData } from "./services";
import { submitToolJob } from "./submit";

import GModal from "../BaseComponents/GModal.vue";
import ToolRecommendation from "../ToolRecommendation.vue";
import ToolCard from "./ToolCard.vue";
import ToolFormTags from "./ToolFormTags.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import ButtonSpinner from "@/components/Common/ButtonSpinner.vue";
import Heading from "@/components/Common/Heading.vue";
import FormSelect from "@/components/Form/Elements/FormSelect.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import FormElement from "@/components/Form/FormElement.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ToolEntryPoints from "@/components/ToolEntryPoints/ToolEntryPoints.vue";

const IMMUTABLE_HISTORY_MSG =
    "This history is immutable and you cannot run tools in it. Please switch to a different history." as const;

const props = defineProps<{
    id: string;
    uuid?: string;
    version?: string;
    jobId?: string;
}>();

const { config, isLoaded: isConfigLoaded } = storeToRefs(useConfigStore());
const route = useRoute();
const router = useRouter();

const { getCredentialsExecutionContextForTool } = useUserToolsServiceCredentialsStore();

const disabled = ref(false);
const loading = ref(false);
const showLoading = ref(true);
const showForm = ref(false);
const showEntryPoints = ref(false);
const showRecommendation = ref(false);
const showError = ref(false);
const showExecuting = ref(false);
// TODO: Needs to be typed
const formConfig = ref<any>({});
const formData = ref<FormData | undefined>(undefined);
const remapAllowed = ref<boolean | "job_produced_collection_elements" | null>(false);
const errorTitle = ref<string | null>(null);
const errorContent = ref<any>(null);
const errorMessage = ref("");
const messageShow = ref(false);
const messageVariant = ref("");
const messageText = ref("");
const useCachedJobs = ref(false);
const useEmail = ref(false);
const useJobRemapping = ref(false);
const dataManagerMode = ref("populate");
const entryPoints = ref<JobResponse["jobs"]>([]);
const submissionRequestFailed = ref(false);
const validationInternal = ref<[string, string] | null>(null);
const validationScrollTo = ref<[string, string] | null>(null);
const currentVersion = ref(props.version);
const preferredObjectStoreId = ref<string | null>(null);
const bundleOptions = ref([
    { label: "populate", value: "populate" },
    { label: "bundle", value: "bundle" },
]);
const tags = ref<string[]>([]);
const formConfigInitialized = ref(false);

const tourStore = useTourStore();
const jobStore = useJobStore();
const historyStore = useHistoryStore();
const userStore = useUserStore();

const { currentUser } = storeToRefs(userStore);
const { currentHistoryId, currentHistory } = storeToRefs(historyStore);
const { lastUpdateTime } = storeToRefs(useHistoryItemsStore());
const { currentTour } = storeToRefs(tourStore);

const toolName = computed(() => formConfig.value.name);

const toolId = computed(() => {
    // ensure version is included in tool id, otherwise form inputs are
    // not re-rendered when versions change.
    const { id, version } = formConfig.value;
    return id.endsWith(version) ? id : `${id}/${version}`;
});

const toolUuid = computed(() => props.uuid || formConfig.value.uuid);

const tooltip = computed(() => {
    if (!canMutateHistory.value) {
        return IMMUTABLE_HISTORY_MSG;
    }
    if (
        (formConfig.value.errors && Object.values(formConfig.value.errors).length > 0) ||
        validationInternal.value?.length
    ) {
        return "Please resolve highlighted issues before running the tool.";
    }
    if (formConfig.value.credentials?.length) {
        const { hasUserProvidedAllRequiredServiceCredentials } = useUserToolCredentials(
            formConfig.value.id,
            formConfig.value.version,
        );
        if (!hasUserProvidedAllRequiredServiceCredentials.value) {
            return "Please provide all required credentials before running the tool.";
        }
    }
    if (showExecuting.value) {
        return "Tool is being executed...";
    }
    return `Run tool: ${toolName.value} (${formConfig.value.version})`;
});

const emailAllowed = computed(() => config.value.server_mail_configured && !currentUser.value?.isAnonymous);

const errorContentPretty = computed(() => JSON.stringify(errorContent.value, null, 4));

const remapTitle = computed(() => {
    if (remapAllowed.value === "job_produced_collection_elements") {
        return "Replace elements in collection?";
    } else {
        return "Resume dependencies from this job?";
    }
});

const remapHelp = computed(() => {
    if (remapAllowed.value === "job_produced_collection_elements") {
        return "The previous run of this tool failed. Use this option to replace the failed element(s) in the dataset collection that were produced during the previous tool run.";
    } else {
        return "The previous run of this tool failed and other tools were waiting for it to finish successfully. Use this option to resume those tools using the new output(s) of this tool run.";
    }
});

const initialized = computed(() => formData.value !== undefined);

const showNoToolParametersAlert = computed(() => !loading.value && formConfig.value?.inputs?.length === 0);

const canMutateHistory = computed(() => (currentHistory.value ? canMutateHistoryMethod(currentHistory.value) : false));

const hasCredentialsErrors = computed(() => {
    if (formConfig.value.credentials?.length) {
        const { hasUserProvidedAllRequiredServiceCredentials } = useUserToolCredentials(
            formConfig.value.id,
            formConfig.value.version,
        );
        return !hasUserProvidedAllRequiredServiceCredentials.value;
    }
    return false;
});

const hasConfigOrValErrors = computed(
    () =>
        (formConfig.value.errors && Object.values(formConfig.value.errors).length > 0) ||
        validationInternal.value?.length,
);

const runButtonDisabled = computed(
    () => disabled.value || !canMutateHistory.value || hasConfigOrValErrors.value || hasCredentialsErrors.value,
);

watch([() => currentHistoryId.value, () => lastUpdateTime.value], () => {
    onHistoryChange();
});

// ...mapActions(useJobStore, ["saveLatestResponse"]),
// ...mapActions(useTourStore, ["setTour"]),
// ...mapActions(useHistoryStore, ["startWatchingHistory"]),
// ...mapActions(useUserStore, ["addRecentTool"]),

function onHistoryChange() {
    if (initialized.value) {
        console.debug(`ToolForm::onHistoryChange - Loading history changes. [${props.id}]`);
        onUpdate();
    }
}

function onValidation(validationFromChild: [string, string] | null) {
    validationInternal.value = validationFromChild;
}

async function onChange(newData: FormData, refreshRequest?: boolean) {
    formData.value = newData;
    if (refreshRequest) {
        await onUpdate();
    } else if (
        formConfigInitialized.value &&
        formConfig.value.errors &&
        Object.values(formConfig.value.errors).length > 0
    ) {
        // Clear stale backend errors when the user edits. Scoped to backend errors only;
        // client-side validation errors are not wiped here.
        formConfig.value.errors = null;
    }
    formConfigInitialized.value = true;
}

async function onUpdate() {
    disabled.value = true;
    console.debug("ToolForm - Updating input parameters.", formData.value);
    try {
        const data = await updateToolFormData(
            formConfig.value.id,
            toolUuid.value,
            currentVersion.value,
            currentHistoryId.value,
            formData.value,
        );

        formConfig.value = data;
    } catch (error) {
        // TODO: Add error handling here
    } finally {
        disabled.value = false;
    }
}

/**
 * Handle a "load more" request from a paginated data parameter dropdown.
 * Re-fetches the form with `options_pagination` set for the requested
 * parameter (keyed by full ``|``-separated dotted path so nested params
 * under conditionals/repeats/sections work too), then walks both the
 * response and the local `formConfig.inputs` to append the new options
 * into the matching parameter's option list.
 */
async function onLoadMore(payload: { name: string; src: string; offset: number; limit: number; search?: string }) {
    const spec = { offset: payload.offset, limit: payload.limit, search: payload.search || undefined };

    const optionsPagination = { [payload.name]: { [payload.src]: spec } };
    try {
        const data = await updateToolFormData(
            formConfig.value.id,
            toolUuid.value,
            currentVersion.value,
            currentHistoryId.value,
            formData.value,
            optionsPagination,
        );
        mergeFetchedOptions(payload.name, payload.src, data);
    } catch (error) {
        // TODO: Add error handling here
    }
}

/**
 * Handle the user typing in the dropdown's search box. Refetch the
 * parameter's options against the backend with the search filter, then
 * MERGE (not replace) the server matches into the already-loaded options.
 * Merging keeps the list non-empty and preserves any already-loaded or
 * selected options, so the multiselect (and its focused search input) is
 * never unmounted mid-typing; the client-side filter still narrows the
 * union down to the typed query. An empty query fetches the default first
 * page. Debounced upstream in ``FormSelect``.
 */
async function onSearchChange(payload: { name: string; src: string; query: string; limit: number }) {
    const spec = { offset: 0, limit: payload.limit, search: payload.query || undefined };

    const optionsPagination = { [payload.name]: { [payload.src]: spec } };
    try {
        const data = await updateToolFormData(
            formConfig.value.id,
            toolUuid.value,
            currentVersion.value,
            currentHistoryId.value,
            formData.value,
            optionsPagination,
        );
        mergeFetchedOptions(payload.name, payload.src, data);
    } catch (error) {
        // TODO: Add error handling here
    }
}

/**
 * Merge a freshly fetched page of options (from load-more or search) into
 * the matching parameter's option list, de-duplicating by ``id``/``src``.
 * Both callers merge rather than replace so the dropdown never empties out
 * from under an open multiselect (which would unmount its focused input),
 * and so a beyond-the-page selection stays visible. Refreshes the form
 * afterwards so the rendered clone picks up the new options (see
 * ``refreshInputs``).
 */
function mergeFetchedOptions(name: string, src: string, data: any) {
    // TODO: Type `data` here with the same type as `formConfig`

    const newInput: FormInputNode | null = findInputByDottedName(data.inputs, name) as FormInputNode | null;
    const target: FormInputNode | null = findInputByDottedName(formConfig.value.inputs, name) as FormInputNode | null;
    if (!newInput || !target) {
        return;
    }

    // The paginated/searched params that reach here are always data params, so the entries are `DataOption`
    const existing = (target.options?.[src] as DataOption[] | undefined) ?? [];
    const incoming = (newInput.options?.[src] as DataOption[] | undefined) ?? [];
    const seen = new Set(existing.map((o) => `${o.id}_${o.src}`));
    const merged = existing.concat(incoming.filter((o) => !seen.has(`${o.id}_${o.src}`)));
    target.options = { ...target.options, [src]: merged };
    if (newInput.options_meta && newInput.options_meta[src]) {
        target.options_meta = {
            ...(target.options_meta || {}),
            [src]: newInput.options_meta[src],
        };
    }
    refreshInputs();
}

/**
 * Hand ``FormDisplay`` a fresh ``inputs`` array reference after mutating a
 * parameter's ``options``/``options_meta`` in place. ``FormDisplay`` renders
 * from an internal *clone* of ``inputs`` that is only re-synced by its
 * ``watch(() => props.inputs)``, which fires on array identity change, not on
 * deep mutation. Without this bump the paginated / searched options are
 * fetched but never reach the dropdown (issue #23135).
 */
function refreshInputs() {
    formConfig.value.inputs = [...formConfig.value.inputs];
}

function onChangeVersion(newVersion: string) {
    requestTool(newVersion);
}

async function requestTool(newVersion?: string) {
    currentVersion.value = newVersion || currentVersion.value;
    disabled.value = true;
    loading.value = true;

    try {
        const data = await getToolFormData(
            props.id || toolUuid.value,
            currentVersion.value,
            props.jobId,
            currentHistoryId.value,
            toolUuid.value,
        );
        currentVersion.value = data.version;
        formConfig.value = data;
        remapAllowed.value = props.jobId && data.job_remap;
        showForm.value = true;
        messageShow.value = false;

        if (newVersion) {
            messageVariant.value = "success";
            messageText.value = `Now you are using '${data.name}' version ${data.version}, id '${data.id}'.`;
        }
    } catch (error) {
        messageVariant.value = "danger";
        messageText.value = `Loading tool ${props.id} failed: ${error}`;
        messageShow.value = true;
    } finally {
        disabled.value = false;
        loading.value = false;
        showLoading.value = false;
    }
}

function onUpdatePreferredObjectStoreId(preferredId: string | null) {
    preferredObjectStoreId.value = preferredId;
}

async function onExecute() {
    // If a tour is active that was generated for this tool, end it.
    if (currentTour.value?.id.startsWith(`tool-generated-${formConfig.value.id}`)) {
        tourStore.setTour(undefined);
    }

    if (validationInternal.value) {
        validationScrollTo.value = validationInternal.value.slice() as [string, string];
        return;
    }
    showExecuting.value = true;
    userStore.addRecentTool(formConfig.value?.id);

    const jobDef: JobRequest = {
        tool_id: formConfig.value.id,
        tool_uuid: toolUuid.value,
        tool_version: formConfig.value.version,
        history_id: currentHistoryId.value,
        use_cached_jobs: useCachedJobs.value || false,
        send_email_notification: useEmail.value || false,
        rerun_remap_job_id: useJobRemapping.value ? props.jobId : undefined,
        preferred_object_store_id: preferredObjectStoreId.value || undefined,
        tags: tags.value?.length ? tags.value : undefined,
        data_manager_mode: dataManagerMode.value === "bundle" ? dataManagerMode.value : undefined,
        credentials_context: formConfig.value.credentials?.length
            ? (getCredentialsExecutionContextForTool(formConfig.value.id, formConfig.value.version) as unknown as {
                  [key: string]: unknown;
              }[])
            : undefined,
        strict: true,
    };

    console.debug("toolForm::onExecute()", jobDef);
    // TODO: Is this really needed?
    const prevRoute = route.fullPath;

    try {
        const jobResponse: JobResponse = await submitToolJob({
            jobDef,
            formConfig: formConfig.value,
            formData: formData.value,
        });
        jobResponse.produces_entry_points = formConfig.value.model_class === "InteractiveTool";

        submissionRequestFailed.value = false;
        showExecuting.value = false;
        historyStore.startWatchingHistory();

        if (jobResponse.produces_entry_points) {
            showEntryPoints.value = true;
            entryPoints.value = jobResponse.jobs;
        }

        const nJobs = jobResponse.jobs ? jobResponse.jobs.length : 0;
        const nErrors = jobResponse.errors?.length || 0;
        if (nJobs > 0 && nErrors === 0) {
            showForm.value = false;
            jobStore.saveLatestResponse({
                jobDef,
                jobResponse,
                toolName: toolName.value,
            });
        } else if (nErrors > 0) {
            showError.value = true;
            showForm.value = true;
            errorTitle.value =
                nJobs > 0
                    ? `Job submission for ${nErrors} out of ${nJobs + nErrors} jobs failed.`
                    : "Job submission rejected.";
            errorContent.value = jobResponse.errors;
            return;
        }

        if (prevRoute === route.fullPath) {
            router.push(`/jobs/submission/success`);
        } else {
            if (parseBool(config.value.enable_tool_recommendations)) {
                showRecommendation.value = true;
            }
            if (document.querySelector("#center")) {
                document.querySelector("#center")!.scrollTop = 0;
            }
        }
    } catch (error) {
        const e = error as any;

        showExecuting.value = false;

        const message = errorMessageAsString(e);

        // Check for structured error data from both axios responses and tool request failures
        const errorData = e?.response?.data?.err_data || e?.err_data;
        if (errorData) {
            const errorEntries = Object.entries(errorData);
            if (errorEntries.length > 0) {
                errorMessage.value = message;
                submissionRequestFailed.value = true;
                validationScrollTo.value = errorEntries[0] as [string, string];
                return;
            }
        }

        if (message) {
            errorMessage.value = message;
            submissionRequestFailed.value = true;
            showError.value = true;
            errorTitle.value = "Job submission failed.";
            errorContent.value = jobDef;
            return;
        }

        showError.value = true;
        errorTitle.value = "Job submission failed.";
        errorContent.value = message || jobDef;
    }
}

requestTool();
</script>

<template>
    <div v-if="currentUser && currentHistoryId && isConfigLoaded">
        <b-alert :show="messageShow" :variant="messageVariant">
            {{ messageText }}
        </b-alert>
        <b-alert v-if="!showLoading && !canMutateHistory" show variant="warning">
            {{ localize(IMMUTABLE_HISTORY_MSG) }}
        </b-alert>
        <LoadingSpan v-if="showLoading" message="Loading Tool" />
        <div v-if="showEntryPoints">
            <ToolEntryPoints v-for="job in entryPoints" :key="job.id" :job-id="job.id" />
        </div>
        <GModal :show.sync="showError" size="medium" :title="localize(errorTitle)" fixed-height>
            <b-alert v-if="errorMessage" show variant="danger">
                {{ errorMessage }}
            </b-alert>
            <b-alert v-if="submissionRequestFailed" show variant="warning">
                The server could not complete this request. Please verify your parameter settings, retry submission and
                contact the Galaxy Team if this error persists. A transcript of the submitted data is shown below.
            </b-alert>
            <small class="text-muted">
                <pre>{{ errorContentPretty }}</pre>
            </small>
        </GModal>
        <ToolRecommendation v-if="showRecommendation" :tool-id="formConfig.id" />
        <ToolCard
            v-if="showForm"
            :id="formConfig.id"
            :version="formConfig.version"
            :tool-uuid="uuid"
            :title="formConfig.name"
            :description="formConfig.description"
            :options="formConfig"
            :message-text="messageText"
            :message-variant="messageVariant"
            :disabled="disabled || showExecuting"
            :allow-object-store-selection="config.object_store_allows_id_selection"
            :preferred-object-store-id="preferredObjectStoreId || undefined"
            allow-generated-tours
            itemscope="itemscope"
            itemtype="https://schema.org/CreativeWork"
            @updatePreferredObjectStoreId="onUpdatePreferredObjectStoreId"
            @onChangeVersion="onChangeVersion">
            <div class="mt-2 mb-4">
                <Heading v-localize h2 separator bold size="sm"> Tool Parameters </Heading>

                <GAlert v-if="showNoToolParametersAlert" show variant="info" data-description="no tool parameters">
                    This tool requires no input parameters and can be run as is.
                </GAlert>

                <FormDisplay
                    :id="toolId"
                    :inputs="formConfig.inputs"
                    :errors="formConfig.errors"
                    :loading="loading"
                    :validation-scroll-to="validationScrollTo"
                    :warnings="formConfig.warnings"
                    @load-more="onLoadMore"
                    @search-change="onSearchChange"
                    @onChange="onChange"
                    @onValidation="onValidation" />
            </div>

            <div class="mt-2 mb-4">
                <Heading v-localize h2 separator bold size="sm"> Additional Options </Heading>
                <FormElement
                    v-if="emailAllowed"
                    id="send_email_notification"
                    v-model="useEmail"
                    :title="localize('Email notification')"
                    :help="localize('Send an email notification when the job completes.')"
                    type="boolean" />
                <FormElement
                    v-if="remapAllowed"
                    id="rerun_remap_job_id"
                    v-model="useJobRemapping"
                    :title="remapTitle"
                    :help="remapHelp"
                    type="boolean" />
                <FormElement
                    id="use_cached_job"
                    v-model="useCachedJobs"
                    :title="localize('Attempt to re-use jobs with identical parameters?')"
                    :help="localize('This may skip executing jobs that you have already run.')"
                    type="boolean" />
                <FormSelect
                    v-if="formConfig.model_class === 'DataManagerTool'"
                    id="data_manager_mode"
                    v-model="dataManagerMode"
                    :options="bundleOptions"
                    :title="localize('Create dataset bundle instead of adding data table to loc file ?')"></FormSelect>
                <ToolFormTags :tags.sync="tags" />
            </div>
            <template v-slot:buttons>
                <ButtonSpinner
                    id="execute"
                    class="text-nowrap"
                    :title="localize('Run Tool')"
                    data-description="run tool button"
                    :disabled="runButtonDisabled"
                    size="small"
                    :wait="showExecuting"
                    :tooltip="tooltip"
                    @onClick="onExecute" />
            </template>
            <template v-slot:footer>
                <ButtonSpinner
                    :title="localize('Run Tool')"
                    class="mt-3 mb-3"
                    :disabled="runButtonDisabled"
                    :wait="showExecuting"
                    :tooltip="tooltip"
                    @onClick="onExecute" />
            </template>
        </ToolCard>
    </div>
</template>
