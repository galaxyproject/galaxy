<template>
    <ConfigProvider v-slot="{ config }">
        <CurrentUser v-slot="{ user }">
            <UserHistories v-if="user" v-slot="{ currentHistoryId }" :user="user">
                <div v-if="currentHistoryId">
                    <b-alert :show="messageShow" :variant="messageVariant">
                        {{ messageText }}
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
                            The server could not complete this request. Please verify your parameter settings, retry
                            submission and contact the Galaxy Team if this error persists. A transcript of the submitted
                            data is shown below.
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
                                    :validation-scroll-to="validationScrollTo"
                                    @onChange="onChange"
                                    @onValidation="onValidation" />
                            </div>

                            <div
                                v-if="emailAllowed(config, user) || remapAllowed || reuseAllowed(user)"
                                class="mt-2 mb-4">
                                <Heading h2 separator bold size="sm"> Additional Options </Heading>
                                <FormElement
                                    v-if="emailAllowed(config, user)"
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
                                    v-if="reuseAllowed(user)"
                                    id="use_cached_job"
                                    v-model="useCachedJobs"
                                    title="Attempt to re-use jobs with identical parameters?"
                                    help="This may skip executing jobs that you have already run."
                                    type="boolean" />
                            </div>
                        </template>
                        <template v-slot:header-buttons>
                            <ButtonSpinner
                                :title="runButtonTitle"
                                class="btn-sm"
                                :wait="showExecuting"
                                :tooltip="tooltip"
                                @onClick="onExecute(config, currentHistoryId)" />
                        </template>
                        <template v-slot:buttons>
                            <ButtonSpinner
                                id="execute"
                                :title="runButtonTitle"
                                class="mt-3 mb-3"
                                :wait="showExecuting"
                                :tooltip="tooltip"
                                @onClick="onExecute(config, currentHistoryId)" />
                        </template>
                    </ToolCard>
                </div>
            </UserHistories>
        </CurrentUser>
    </ConfigProvider>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import { getGalaxyInstance } from "app";
import { useHistoryItemsStore } from "stores/history/historyItemsStore";
import { useJobStore } from "stores/jobStore";
import { mapState, mapActions } from "pinia";
import { mapGetters } from "vuex";
import { getToolFormData, getToolInputs, updateToolFormData, submitJob, submitToolRequest } from "./services";
import { allowCachedJobs } from "./utilities";
import { refreshContentsWrapper } from "utils/data";
import ToolCard from "./ToolCard";
import ButtonSpinner from "components/Common/ButtonSpinner";
import CurrentUser from "components/providers/CurrentUser";
import ConfigProvider from "components/providers/ConfigProvider";
import LoadingSpan from "components/LoadingSpan";
import FormDisplay from "components/Form/FormDisplay";
import FormElement from "components/Form/FormElement";
import ToolEntryPoints from "components/ToolEntryPoints/ToolEntryPoints";
import ToolRecommendation from "../ToolRecommendation";
import UserHistories from "components/providers/UserHistories";
import Heading from "components/Common/Heading";
import { structuredInputs } from "./structured";

export default {
    components: {
        ButtonSpinner,
        CurrentUser,
        ConfigProvider,
        LoadingSpan,
        FormDisplay,
        ToolCard,
        FormElement,
        ToolEntryPoints,
        ToolRecommendation,
        UserHistories,
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
    data() {
        return {
            disabled: false,
            initialized: false,
            showLoading: true,
            showForm: false,
            showEntryPoints: false,
            showRecommendation: false,
            showError: false,
            showExecuting: false,
            formConfig: {},
            formData: {},
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
            entryPoints: [],
            jobDef: {},
            jobResponse: {},
            validationInternal: null,
            validationScrollTo: null,
            currentVersion: this.version,
            preferredObjectStoreId: null,
            toolInputs: null,
            submissionStateMessage: null,
        };
    },
    computed: {
        ...mapState(useHistoryItemsStore, ["getLastUpdateTime"]),
        ...mapGetters("history", ["currentHistoryId"]),
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
        runButtonTitle() {
            if (this.showExecuting) {
                if (this.submissionStateMessage) {
                    return this.submissionStateMessage;
                } else {
                    return "Run Tool";
                }
            } else {
                return "Run Tool";
            }
        },
    },
    watch: {
        currentHistoryId() {
            this.onHistoryChange();
        },
        getLastUpdateTime() {
            this.onHistoryChange();
        },
    },
    created() {
        this.requestTool().then(() => {
            this.initialized = true;
            console.debug(`ToolForm::created - Started listening to history changes. [${this.id}]`);
        });
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
        waitOnRequest(response, requestContent, config, prevRoute) {
            const toolRequestId = response.tool_request_id;
            const handleRequestState = (toolRequestStateResponse) => {
                const state = toolRequestStateResponse.data;
                console.log(`state is ${state}`);
                if (["new"].indexOf(state) !== -1) {
                    setTimeout(doRequestCheck, 1000);
                } else if (state == "failed") {
                    this.handleError(null, requestContent);
                } else {
                    refreshContentsWrapper();
                    this.showForm = false;
                    this.showSuccess = true;
                    this.handleSubmissionComplete(config, prevRoute);
                }
            };
            const doRequestCheck = () => {
                axios
                    .get(`${getAppRoot()}api/tool_requests/${toolRequestId}/state`)
                    .then(handleRequestState)
                    .catch((e) => this.handleError(e, requestContent));
            };
            setTimeout(doRequestCheck, 1000);
        },
        requestTool(newVersion) {
            this.currentVersion = newVersion || this.currentVersion;
            this.disabled = true;
            console.debug("ToolForm - Requesting tool.", this.id);
            getToolInputs(this.id, this.currentVersion).then((data) => {
                this.toolInputs = data;
            });
            return getToolFormData(this.id, this.currentVersion, this.job_id, this.history_id)
                .then((data) => {
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
                    this.showLoading = false;
                });
        },
        onUpdatePreferredObjectStoreId(preferredObjectStoreId) {
            this.preferredObjectStoreId = preferredObjectStoreId;
        },
        handleSubmissionComplete(config, prevRoute) {
            const changeRoute = prevRoute === this.$route.fullPath;
            if (changeRoute) {
                this.$router.push(`/jobs/submission/success`);
            } else {
                if ([true, "true"].includes(config.enable_tool_recommendations)) {
                    this.showRecommendation = true;
                }
                document.querySelector(".center-panel").scrollTop = 0;
            }
        },
        handleError(e, errorContent) {
            this.errorMessage = e?.response?.data?.err_msg;
            this.showExecuting = false;
            this.submissionStateMessage = null;
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
                this.errorContent = errorContent;
            }
        },
        onExecute(config, historyId) {
            if (this.validationInternal) {
                this.validationScrollTo = this.validationInternal.slice();
                return;
            }
            this.showExecuting = true;
            this.submissionStateMessage = "Preparing Request";
            const inputs = {
                ...this.formData,
            };
            const toolId = this.formConfig.id;
            const toolVersion = this.formConfig.version;
            let validatedInputs = null;
            try {
                validatedInputs = structuredInputs(inputs, this.toolInputs);
            } catch {
                // failed validation, just use legacy API
            }
            const prevRoute = this.$route.fullPath;
            if (validatedInputs) {
                const toolRequest = {
                    history_id: historyId,
                    tool_id: toolId,
                    tool_version: toolVersion,
                    inputs: validatedInputs,
                };
                if (this.useCachedJobs) {
                    toolRequest.use_cached_jobs = true;
                }
                if (this.preferredObjectStoreId) {
                    toolRequest.preferred_object_store_id = this.preferredObjectStoreId;
                }
                this.submissionStateMessage = "Sending Request";
                submitToolRequest(toolRequest).then(
                    (jobResponse) => {
                        this.submissionStateMessage = "Processing Request";
                        console.log(jobResponse);
                        this.waitOnRequest(jobResponse, toolRequest, config, prevRoute);
                    },
                    (e) => {
                        this.handleError(e, toolRequest);
                    }
                );
            } else {
                const jobDef = {
                    history_id: historyId,
                    tool_id: toolId,
                    tool_version: toolVersion,
                    inputs: inputs,
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
                console.debug("toolForm::onExecute()", jobDef);
                submitJob(jobDef).then(
                    (jobResponse) => {
                        this.showExecuting = false;
                        refreshContentsWrapper();
                        if (jobResponse.produces_entry_points) {
                            this.showEntryPoints = true;
                            this.entryPoints = jobResponse.jobs;
                        }
                        const nJobs = jobResponse && jobResponse.jobs ? jobResponse.jobs.length : 0;
                        if (nJobs > 0) {
                            this.showForm = false;
                            this.showSuccess = true;
                            this.jobDef = jobDef;
                            this.jobResponse = jobResponse;
                            const response = {
                                jobDef: this.jobDef,
                                jobResponse: this.jobResponse,
                                toolName: this.toolName,
                            };
                            this.saveLatestResponse(response);
                        } else {
                            this.showError = true;
                            this.showForm = true;
                            this.errorTitle = "Job submission rejected.";
                            this.errorContent = jobResponse;
                        }
                        this.handleSubmissionComplete(config, prevRoute);
                    },
                    (e) => {
                        this.handleError(e, jobDef);
                    }
                );
            }
        },
    },
};
</script>
