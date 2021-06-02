<template>
    <CurrentUser v-slot="{ user }">
        <div>
            <LoadingSpan v-if="showLoading" message="Loading Tool" />
            <div v-if="showEntryPoints">
                <ToolEntryPoints v-for="job in entryPoints" :job-id="job.id" :key="job.id" />
            </div>
            <ToolSuccess v-if="showSuccess" :job-def="jobDef" :job-response="jobResponse" :tool-name="toolName" />
            <Webhook v-if="showSuccess" type="tool" :tool-id="jobDef.tool_id" />
            <div v-if="showError" class="errormessagelarge">
                <p>
                    The server could not complete the request. Please contact the Galaxy Team if this error persists.
                    {{ errorTitle | l }}
                </p>
                <pre>{{ errorContentPretty }}</pre>
            </div>
            <ToolRecommendation v-if="showRecommendation" :tool-id="id" />
            <ToolCard
                v-if="showForm"
                :id="formConfig.id"
                :user="user"
                :version="formConfig.version"
                :title="formConfig.name"
                :description="formConfig.description"
                :options="formConfig"
                :message-text="messageText"
                :message-variant="messageVariant"
                @onChangeVersion="onChangeVersion"
                @onUpdateFavorites="onUpdateFavorites"
                itemscope="itemscope"
                itemtype="https://schema.org/CreativeWork"
            >
                <template v-slot:body>
                    <Form
                        :id="formConfig.id"
                        :inputs="inputs"
                        :validation-errors="validationErrors"
                        @onChange="onChange"
                    />
                    <FormElement
                        v-if="emailAllowed"
                        id="send_email_notification"
                        title="Email notification"
                        help="Send an email notification when the job completes."
                        type="boolean"
                        value="false"
                        @onChange="onChangeEmail"
                    />
                    <FormElement
                        v-if="remapAllowed"
                        id="rerun_remap_job_id"
                        :title="remapTitle"
                        :help="remapHelp"
                        type="boolean"
                        value="false"
                        @onChange="onChangeRemap"
                    />
                    <FormElement
                        v-if="reuseAllowed"
                        id="use_cached_job"
                        title="Attempt to re-use jobs with identical parameters?"
                        help="This may skip executing jobs that you have already run."
                        type="boolean"
                        value="false"
                        @onChange="onChangeReuse"
                    />
                </template>
                <template v-slot:buttons>
                    <ButtonSpinner id="execute" title="Execute" @onClick="onExecute" :wait="showExecuting" />
                </template>
            </ToolCard>
        </div>
    </CurrentUser>
</template>

<script>
import Scroller from "vue-scrollto";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import { getTool, submitJob } from "./services";
import { send } from "./utilities";
import ToolCard from "./ToolCard";
import ButtonSpinner from "components/Common/ButtonSpinner";
import CurrentUser from "components/providers/CurrentUser";
import LoadingSpan from "components/LoadingSpan";
import Form from "components/Form/Form";
import FormElement from "components/Form/FormElement";
import ToolSuccess from "./ToolSuccess";
import Webhook from "components/Common/Webhook";

export default {
    components: {
        ButtonSpinner,
        CurrentUser,
        LoadingSpan,
        Form,
        ToolCard,
        FormElement,
        ToolSuccess,
        Webhook,
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
    },
    data() {
        return {
            showLoading: true,
            showForm: false,
            showEntryPoints: false,
            showRecommendation: false,
            showSuccess: false,
            showError: false,
            showExecuting: false,
            error: null,
            formConfig: {},
            formData: {},
            errorTitle: "",
            errorContent: null,
            messageVariant: "",
            messageText: "",
            reuse: false,
            email: false,
            remap: false,
            entryPoints: [],
            jobDef: {},
            jobResponse: {},
            validationErrors: {},
            currentVersion: this.version,
        };
    },
    created() {
        this.requestTool();
        const Galaxy = getGalaxyInstance();
        if (Galaxy.currHistoryPanel) {
            Galaxy.currHistoryPanel.collection.on("change", () => {
                this.requestTool();
            });
        }
    },
    computed: {
        toolName() {
            return this.formConfig.name;
        },
        errorContentPretty() {
            return JSON.stringify(this.errorContent, null, 4);
        },
        emailAllowed() {
            const Galaxy = getGalaxyInstance();
            return Galaxy.config.server_mail_configured && !Galaxy.user.isAnonymous();
        },
        inputs() {
            return this.formConfig.inputs;
        },
        remapAllowed() {
            return this.job_id && this.formConfig.job_remap;
        },
        remapLabel() {
            if (this.formConfig.job_remap === "job_produced_collection_elements") {
                return "Replace elements in collection ?";
            } else {
                return "Resume dependencies from this job ?";
            }
        },
        remapHelp() {
            if (this.formConfig.job_remap === "job_produced_collection_elements") {
                return "The previous run of this tool failed. Use this option to replace the failed element(s) in the dataset collection that were produced during the previous tool run.";
            } else {
                return "The previous run of this tool failed and other tools were waiting for it to finish successfully. Use this option to resume those tools using the new output(s) of this tool run.";
            }
        },
        reuseAllowed() {
            const Galaxy = getGalaxyInstance();
            if (Galaxy.user.attributes.preferences && "extra_user_preferences" in Galaxy.user.attributes.preferences) {
                const extra_user_preferences = JSON.parse(Galaxy.user.attributes.preferences.extra_user_preferences);
                const keyCached = "use_cached_job|use_cached_job_checkbox";
                const hasCachedJobs = keyCached in extra_user_preferences;
                return hasCachedJobs ? extra_user_preferences[keyCached] : false;
            } else {
                return false;
            }
        },
    },
    methods: {
        onChange(newData) {
            this.formData = newData;
        },
        onChangeVersion(newVersion) {
            this.requestTool(newVersion);
        },
        onChangeEmail(email) {
            this.email = email;
        },
        onChangeRemap(remap) {
            this.remap = remap ? this.job_id : null;
        },
        onChangeReuse(reuse) {
            this.reuse = reuse;
        },
        onUpdateFavorites(user, newFavorites) {
            user.preferences["favorites"] = newFavorites;
        },
        requestTool(newVersion) {
            this.currentVersion = newVersion || this.currentVersion;
            getTool(this.id, currentVersion, this.job_id).then((data) => {
                this.formConfig = data;
                this.showLoading = false;
                this.showForm = true;
                if (newVersion) {
                    this.messageVariant = "success";
                    this.messageText = `Now you are using '${data.name}' version ${data.version}, id '${data.id}'.`;
                }
            });
        },
        onExecute() {
            this.showExecuting = true;
            const options = this.formData;
            const Galaxy = getGalaxyInstance();
            const history_id = Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model.id;
            const jobDef = {
                history_id: history_id,
                tool_id: this.formConfig.id,
                tool_version: this.formConfig.version,
                inputs: this.formData,
            };
            if (this.formConfig.action !== `${getAppRoot()}tool_runner/index`) {
                send(options, jobDef);
                return;
            }
            Galaxy.emit.debug("tool-form::submit()", "Validation complete.", jobDef);
            submitJob(jobDef).then(
                (jobResponse) => {
                    if (Galaxy.currHistoryPanel) {
                        Galaxy.currHistoryPanel.refreshContents();
                    }
                    this.showForm = false;
                    if (jobResponse.produces_entry_points) {
                        this.showEntryPoints = true;
                        this.entryPoints = jobResponse.jobs;
                    }
                    const nJobs = jobResponse && jobResponse.jobs ? jobResponse.jobs.length : 0;
                    if (nJobs > 0) {
                        this.showSuccess = true;
                        this.jobDef = jobDef;
                        this.jobResponse = jobResponse;
                    } else {
                        this.showError = true;
                        this.errorTitle = "Invalid success response. No jobs found.";
                        this.errorContent = jobResponse;
                    }
                    if ([true, "true"].includes(Galaxy.config.enable_tool_recommendations)) {
                        this.showRecommendation = true;
                    }
                    Scroller.scrollTo("body");
                },
                (e) => {
                    this.showExecuting = false;
                    const errorData = e && e.response && e.response.data && e.response.data.err_data;
                    if (errorData) {
                        this.validationErrors = errorData;
                    } else {
                        this.showError = true;
                        this.showForm = false;
                        this.errorTitle = "Job submission failed";
                        this.errorContent = this.jobDef;
                    }
                }
            );
        },
    },
};
</script>
