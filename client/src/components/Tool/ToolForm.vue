<template>
    <div v-if="currentUser && currentHistoryId && isConfigLoaded">
        <b-alert :show="messageShow" :variant="messageVariant">
            {{ messageText }}
        </b-alert>
        <b-alert v-if="!showLoading && !canMutateHistory" show variant="warning">
            {{ immutableHistoryMessage }}
        </b-alert>
        <LoadingSpan v-if="showLoading" message="Loading Tool" />
        <div v-if="showEntryPoints">
            <ToolEntryPoints v-for="job in entryPoints" :key="job.id" :job-id="job.id" />
        </div>
        <b-modal v-model="showError" size="sm" :title="errorTitle | l" scrollable ok-only>
            <b-alert v-if="errorMessage" show variant="danger">
                {{ errorMessage }}
            </b-alert>
            <b-alert show variant="warning">
                The server could not complete this request. Please verify your parameter settings, retry submission and
                contact the Galaxy Team if this error persists. A transcript of the submitted data is shown below.
            </b-alert>
            <small class="text-muted">
                <pre>{{ errorContentPretty }}</pre>
            </small>
        </b-modal>
        <ToolRecommendation v-if="showRecommendation" :tool-id="formConfig.id" />
        <ToolCard
            v-if="showForm"
            :id="formConfig.id"
            :version="formConfig.version"
            :title="formConfig.name"
            :description="formConfig.description"
            :options="formConfig"
            :message-text="messageText"
            :message-variant="messageVariant"
            :disabled="disabled || showExecuting"
            :allow-object-store-selection="config.object_store_allows_id_selection"
            :preferred-object-store-id="preferredObjectStoreId"
            itemscope="itemscope"
            itemtype="https://schema.org/CreativeWork"
            @updatePreferredObjectStoreId="onUpdatePreferredObjectStoreId"
            @onChangeVersion="onChangeVersion">
            <template v-slot:body>
                <div class="mt-2 mb-4">
                    <Heading h2 separator bold size="sm"> Tool Parameters </Heading>
                    <FormDisplay
                        :id="toolId"
                        :inputs="formConfig.inputs"
                        :errors="formConfig.errors"
                        :loading="loading"
                        :validation-scroll-to="validationScrollTo"
                        :warnings="formConfig.warnings"
                        @onChange="onChange"
                        @onValidation="onValidation" />
                </div>

                <div
                    v-if="emailAllowed(config, currentUser) || remapAllowed || reuseAllowed(currentUser)"
                    class="mt-2 mb-4">
                    <Heading h2 separator bold size="sm"> Additional Options </Heading>
                    <FormElement
                        v-if="emailAllowed(config, currentUser)"
                        id="send_email_notification"
                        v-model="useEmail"
                        title="Email notification"
                        help="Send an email notification when the job completes."
                        type="boolean" />
                    <FormElement
                        v-if="remapAllowed"
                        id="rerun_remap_job_id"
                        v-model="useJobRemapping"
                        :title="remapTitle"
                        :help="remapHelp"
                        type="boolean" />
                    <FormElement
                        v-if="reuseAllowed(currentUser)"
                        id="use_cached_job"
                        v-model="useCachedJobs"
                        title="Attempt to re-use jobs with identical parameters?"
                        help="This may skip executing jobs that you have already run."
                        type="boolean" />
                    <FormSelect
                        v-if="formConfig.model_class === 'DataManagerTool'"
                        id="data_manager_mode"
                        v-model="dataManagerMode"
                        :options="bundleOptions"
                        title="Create dataset bundle instead of adding data table to loc file ?"></FormSelect>
                </div>
            </template>
            <template v-slot:header-buttons>
                <ButtonSpinner
                    id="execute"
                    title="Run Tool"
                    :disabled="!canMutateHistory"
                    class="btn-sm"
                    :wait="showExecuting"
                    :tooltip="tooltip"
                    @onClick="onExecute(config, currentHistoryId)" />
            </template>
            <template v-slot:buttons>
                <ButtonSpinner
                    title="Run Tool"
                    class="mt-3 mb-3"
                    :disabled="!canMutateHistory"
                    :wait="showExecuting"
                    :tooltip="tooltip"
                    @onClick="onExecute(config, currentHistoryId)" />
            </template>
        </ToolCard>
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
import ButtonSpinner from "components/Common/ButtonSpinner";
import Heading from "components/Common/Heading";
import FormDisplay from "components/Form/FormDisplay";
import FormElement from "components/Form/FormElement";
import LoadingSpan from "components/LoadingSpan";
import ToolEntryPoints from "components/ToolEntryPoints/ToolEntryPoints";
import { mapActions, mapState, storeToRefs } from "pinia";
import { useHistoryItemsStore } from "stores/historyItemsStore";
import { useJobStore } from "stores/jobStore";
import { refreshContentsWrapper } from "utils/data";

import { canMutateHistory } from "@/api";
import { useConfigStore } from "@/stores/configurationStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import ToolRecommendation from "../ToolRecommendation";
import { getToolFormData, submitJob, updateToolFormData } from "./services";
import ToolCard from "./ToolCard";
import { allowCachedJobs } from "./utilities";

import FormSelect from "@/components/Form/Elements/FormSelect.vue";

export default {
    components: {
        ButtonSpinner,
        LoadingSpan,
        FormDisplay,
        ToolCard,
        FormElement,
        FormSelect,
        ToolEntryPoints,
        ToolRecommendation,
        Heading,
    },
    props: {
        id: {
            type: String,
            default: null,
        },
        version: {
            type: String,
            default: null,
        },
        job_id: {
            type: String,
            default: null,
        },
        history_id: {
            type: String,
            default: null,
        },
    },
    setup() {
        const { config, isLoaded: isConfigLoaded } = storeToRefs(useConfigStore());
        return { config, isConfigLoaded };
    },
    data() {
        return {
            disabled: false,
            loading: false,
            showLoading: true,
            showForm: false,
            showEntryPoints: false,
            showRecommendation: false,
            showError: false,
            showExecuting: false,
            formConfig: {},
            formData: undefined,
            remapAllowed: false,
            errorTitle: null,
            errorContent: null,
            errorMessage: "",
            messageShow: false,
            messageVariant: "",
            messageText: "",
            useCachedJobs: false,
            useEmail: false,
            useJobRemapping: false,
            dataManagerMode: "populate",
            entryPoints: [],
            jobDef: {},
            jobResponse: {},
            validationInternal: null,
            validationScrollTo: null,
            currentVersion: this.version,
            preferredObjectStoreId: null,
            bundleOptions: [
                { label: "populate", value: "populate" },
                { label: "bundle", value: "bundle" },
            ],
            immutableHistoryMessage:
                "This history is immutable and you cannot run tools in it. Please switch to a different history.",
        };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        ...mapState(useHistoryStore, ["currentHistoryId", "currentHistory"]),
        ...mapState(useHistoryItemsStore, ["lastUpdateTime"]),
        toolName() {
            return this.formConfig.name;
        },
        toolId() {
            // ensure version is included in tool id, otherwise form inputs are
            // not re-rendered when versions change.
            const { id, version } = this.formConfig;
            return id.endsWith(version) ? id : `${id}/${version}`;
        },
        tooltip() {
            if (!this.canMutateHistory) {
                return this.immutableHistoryMessage;
            }
            return `Run tool: ${this.formConfig.name} (${this.formConfig.version})`;
        },
        errorContentPretty() {
            return JSON.stringify(this.errorContent, null, 4);
        },
        remapTitle() {
            if (this.remapAllowed === "job_produced_collection_elements") {
                return "Replace elements in collection?";
            } else {
                return "Resume dependencies from this job?";
            }
        },
        remapHelp() {
            if (this.remapAllowed === "job_produced_collection_elements") {
                return "The previous run of this tool failed. Use this option to replace the failed element(s) in the dataset collection that were produced during the previous tool run.";
            } else {
                return "The previous run of this tool failed and other tools were waiting for it to finish successfully. Use this option to resume those tools using the new output(s) of this tool run.";
            }
        },
        initialized() {
            return this.formData !== undefined;
        },
        canMutateHistory() {
            return this.currentHistory && canMutateHistory(this.currentHistory);
        },
    },
    watch: {
        currentHistoryId() {
            this.onHistoryChange();
        },
        lastUpdateTime() {
            this.onHistoryChange();
        },
    },
    created() {
        this.requestTool();
    },
    methods: {
        ...mapActions(useJobStore, ["saveLatestResponse"]),
        emailAllowed(config, user) {
            return config.server_mail_configured && !user.isAnonymous;
        },
        reuseAllowed(user) {
            return allowCachedJobs(user.preferences);
        },
        onHistoryChange() {
            const Galaxy = getGalaxyInstance();
            if (this.initialized && Galaxy && Galaxy.currHistoryPanel) {
                console.debug(`ToolForm::onHistoryChange - Loading history changes. [${this.id}]`);
                this.onUpdate();
            }
        },
        onValidation(validationInternal) {
            this.validationInternal = validationInternal;
        },
        onChange(newData, refreshRequest) {
            this.formData = newData;
            if (refreshRequest) {
                this.onUpdate();
            }
        },
        onUpdate() {
            this.disabled = true;
            console.debug("ToolForm - Updating input parameters.", this.formData);
            updateToolFormData(this.formConfig.id, this.currentVersion, this.history_id, this.formData)
                .then((data) => {
                    this.formConfig = data;
                })
                .finally(() => {
                    this.disabled = false;
                });
        },
        onChangeVersion(newVersion) {
            this.requestTool(newVersion);
        },
        requestTool(newVersion) {
            this.currentVersion = newVersion || this.currentVersion;
            this.disabled = true;
            this.loading = true;
            console.debug("ToolForm - Requesting tool.", this.id);
            return getToolFormData(this.id, this.currentVersion, this.job_id, this.history_id)
                .then((data) => {
                    this.currentVersion = data.version;
                    this.formConfig = data;
                    this.remapAllowed = this.job_id && data.job_remap;
                    this.showForm = true;
                    this.messageShow = false;
                    if (newVersion) {
                        this.messageVariant = "success";
                        this.messageText = `Now you are using '${data.name}' version ${data.version}, id '${data.id}'.`;
                    }
                })
                .catch((error) => {
                    this.messageVariant = "danger";
                    this.messageText = `Loading tool ${this.id} failed: ${error}`;
                    this.messageShow = true;
                })
                .finally(() => {
                    this.disabled = false;
                    this.loading = false;
                    this.showLoading = false;
                });
        },
        onUpdatePreferredObjectStoreId(preferredObjectStoreId) {
            this.preferredObjectStoreId = preferredObjectStoreId;
        },
        onExecute(config, historyId) {
            if (this.validationInternal) {
                this.validationScrollTo = this.validationInternal.slice();
                return;
            }
            this.showExecuting = true;
            const jobDef = {
                history_id: historyId,
                tool_id: this.formConfig.id,
                tool_version: this.formConfig.version,
                inputs: {
                    ...this.formData,
                },
            };
            if (this.useEmail) {
                jobDef.inputs["send_email_notification"] = true;
            }
            if (this.useJobRemapping) {
                jobDef.inputs["rerun_remap_job_id"] = this.job_id;
            }
            if (this.useCachedJobs) {
                jobDef.inputs["use_cached_job"] = true;
            }
            if (this.preferredObjectStoreId) {
                jobDef.preferred_object_store_id = this.preferredObjectStoreId;
            }
            if (this.dataManagerMode === "bundle") {
                jobDef.data_manager_mode = this.dataManagerMode;
            }
            console.debug("toolForm::onExecute()", jobDef);
            const prevRoute = this.$route.fullPath;
            submitJob(jobDef).then(
                (jobResponse) => {
                    this.showExecuting = false;
                    let changeRoute = false;
                    refreshContentsWrapper();
                    if (jobResponse.produces_entry_points) {
                        this.showEntryPoints = true;
                        this.entryPoints = jobResponse.jobs;
                    }
                    const nJobs = jobResponse && jobResponse.jobs ? jobResponse.jobs.length : 0;
                    if (nJobs > 0) {
                        this.showForm = false;
                        const toolName = this.toolName;
                        this.saveLatestResponse({
                            jobDef,
                            jobResponse,
                            toolName,
                        });
                        changeRoute = prevRoute === this.$route.fullPath;
                    } else {
                        this.showError = true;
                        this.showForm = true;
                        this.errorTitle = "Job submission rejected.";
                        this.errorContent = jobResponse;
                    }
                    if (changeRoute) {
                        this.$router.push(`/jobs/submission/success`);
                    } else {
                        if ([true, "true"].includes(config.enable_tool_recommendations)) {
                            this.showRecommendation = true;
                        }
                        document.querySelector("#center").scrollTop = 0;
                    }
                },
                (e) => {
                    this.errorMessage = e?.response?.data?.err_msg;
                    this.showExecuting = false;
                    let genericError = true;
                    const errorData = e && e.response && e.response.data && e.response.data.err_data;
                    if (errorData) {
                        const errorEntries = Object.entries(errorData);
                        if (errorEntries.length > 0) {
                            this.validationScrollTo = errorEntries[0];
                            genericError = false;
                        }
                    }
                    if (genericError) {
                        this.showError = true;
                        this.errorTitle = "Job submission failed.";
                        this.errorContent = jobDef;
                    }
                }
            );
        },
    },
};
</script>
