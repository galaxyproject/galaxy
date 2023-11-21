<template>
    <div>
        <div v-if="showEntryPoints">
            <ToolEntryPoints v-for="job in entryPoints" :key="job.id" :job-id="job.id" />
        </div>

        <ToolRecommendation v-if="showRecommendation" :tool-id="formConfig.id" />

        <ToolCard
            v-if="showForm"
            :id="formConfig.id"
            :version="formConfig.version"
            :title="formConfig.name"
            :description="formConfig.description"
            :options="formConfig"
            :disabled="disabled || showExecuting"
            :allow-object-store-selection="config.object_store_allows_id_selection"
            :preferred-object-store-id="preferredObjectStoreId"
            @onChangeVersion="onChangeVersion"
            @onSetError="onSetError"
            @updatePreferredObjectStoreId="onUpdatePreferredObjectStoreId">
            <template v-slot:body>
                <slot name="tool-messages" />
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
                </div>
            </template>

            <template v-slot:header-buttons>
                <ButtonSpinner
                    id="execute"
                    title="Run Tool"
                    class="btn-sm"
                    :wait="showExecuting"
                    :tooltip="tooltip"
                    @onClick="onExecute(config, currentHistoryId)" />
            </template>

            <template v-slot:buttons>
                <ButtonSpinner
                    title="Run Tool"
                    class="mt-3 mb-3"
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
import ToolEntryPoints from "components/ToolEntryPoints/ToolEntryPoints";
import { useConfig } from "composables/config";
import { mapActions, mapState } from "pinia";
import { useHistoryItemsStore } from "stores/historyItemsStore";
import { useHistoryStore } from "stores/historyStore";
import { useJobStore } from "stores/jobStore";
import { useUserStore } from "stores/userStore";
import { refreshContentsWrapper } from "utils/data";

import ToolRecommendation from "../ToolRecommendation";
import { submitJob, updateToolFormData } from "./services";
import { allowCachedJobs } from "./utilities";

import ToolCard from "./ToolCard.vue";

export default {
    components: {
        ToolCard,
        ToolRecommendation,
        ToolEntryPoints,
        ButtonSpinner,
        FormDisplay,
        FormElement,
        Heading,
    },
    props: {
        toolConfig: {
            type: Object,
            required: true,
        },
        showTool: {
            type: Boolean,
            required: true,
        },
        disableTool: {
            type: Boolean,
            default: false,
        },
        loading: {
            type: Boolean,
            default: false,
        },
    },
    setup() {
        const { config, isConfigLoaded } = useConfig(true);
        return { config, isConfigLoaded };
    },
    data() {
        return {
            showForm: this.showTool,
            disabled: this.disableTool,
            showEntryPoints: false,
            showRecommendation: false,
            showExecuting: false,
            formConfig: this.toolConfig,
            formData: undefined,
            useCachedJobs: false,
            useEmail: false,
            useJobRemapping: false,
            entryPoints: [],
            validationInternal: null,
            validationScrollTo: null,
            preferredObjectStoreId: null,
        };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        ...mapState(useHistoryStore, ["currentHistoryId"]),
        ...mapState(useHistoryItemsStore, ["lastUpdateTime"]),
        remapAllowed() {
            return this.formConfig.job_remap === true;
        },
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
    },
    watch: {
        toolConfig(newToolConfig) {
            this.formConfig = newToolConfig;
        },
        showTool(newShowTool) {
            this.showForm = newShowTool;
        },
        disableTool(newDisableTool) {
            this.disabled = newDisableTool;
        },
        currentHistoryId() {
            this.onHistoryChange();
        },
        lastUpdateTime() {
            this.onHistoryChange();
        },
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
            updateToolFormData(this.formConfig.id, this.formConfig.version, this.history_id, this.formData)
                .then((data) => {
                    this.formConfig = data;
                })
                .finally(() => {
                    this.disabled = false;
                });
        },
        onChangeVersion(newVersion) {
            this.$emit("onChangeVersion", newVersion);
        },
        onSetError(errorObj) {
            this.$emit("onSetError", errorObj);
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
                        this.showForm = true;
                        this.$emit("onSetError", {
                            dialog: true,
                            message: "",
                            title: "Job submission rejected.",
                            content: jobResponse,
                        });
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
                        this.$emit("onSetError", {
                            dialog: true,
                            message: e?.response?.data?.err_msg,
                            title: "Job submission failed.",
                            content: jobDef,
                        });
                    }
                }
            );
        },
    },
};
</script>
